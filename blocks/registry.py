from __future__ import annotations

import importlib
import re
import textwrap
from collections import defaultdict
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from inspect import isclass
from typing import TYPE_CHECKING, Any, Literal

import graphene
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, Model
from wagtail import blocks

from grapple.helpers import register_streamfield_block

from kausal_common.const import IS_WATCH
from kausal_common.utils import underscore_to_camelcase

from .base import (
    ColumnBlockBase,
    ContentBlockBase,
    DashboardColumnInterface,
    FilterBlockBase,
    FilterBlockInterface,
    GeneralFieldBlockBase,
    GeneralFieldBlockInterface,
)
from .fields import FieldBlockMetaInterface, lazy_field_label

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

    from django.utils.functional import _StrPromise
    from django_stubs_ext import StrOrPromise

    if IS_WATCH:
        from reports.report_formatters import ReportFieldFormatter


def _import(path: str) -> type[Any]:
    """
    Import a class from a module based on a string.

    The string must be in the format path.to.package.ClassWithinPackage
    """
    names = re.match(r'^(.+)\.([^.]+)$', path)
    if not names:
        raise ValueError('Supply path.to.module.and.ClassName as a period-separated Python module path')
    module_name = names.group(1)
    class_name = names.group(2)
    module = importlib.import_module(module_name)
    try:
        return getattr(module, class_name)
    except AttributeError as e:
        msg = f'Class name {class_name} not found within module {module}'
        raise ValueError(msg) from e


class FieldBlockContext(StrEnum):
    REPORT = 'report'
    DASHBOARD = 'dashboard'
    DETAILS = 'details'
    LIST_FILTERS = 'list_filters'


type FieldType = Literal['primitive', 'single', 'many', 'custom']
type FieldRegistryDict = dict[str, ModelFieldProperties]


@dataclass
class BlockConfig:
    has_block: bool = True
    block_class: CustomBlockClassDef | None = None
    """Fixed block class to use."""
    block_class_name: str | None = None
    """The name for the generated block class."""


type BlockConfigMap = dict[FieldBlockContext, BlockConfig]

type CustomBlockClassDef = str | type[blocks.Block] | Callable[[], type[blocks.Block]]


@dataclass
class ModelFieldProperties:
    field_name: str
    field_type: FieldType = 'primitive'
    custom_label: _StrPromise | None = None

    has_dashboard_column_block: bool = True
    has_details_block: bool = True
    has_report_block: bool = True
    has_list_filters_block: bool = True

    dashboard_column_block_class: CustomBlockClassDef | None = None
    details_block_class: CustomBlockClassDef | None = None
    report_block_class: CustomBlockClassDef | None = None
    list_filters_block_class: CustomBlockClassDef | None = None

    report_formatter_class: str | None = None
    dashboard_column_block_class_name: str | None = None

    config: BlockConfigMap = field(init=False)

    def __post_init__(self):
        self.config = {
            FieldBlockContext.DASHBOARD: BlockConfig(
                has_block=self.has_dashboard_column_block,
                block_class=self.dashboard_column_block_class,
                block_class_name=self.dashboard_column_block_class_name,
            ),
            FieldBlockContext.REPORT: BlockConfig(
                has_block=self.has_report_block,
                block_class=self.report_block_class,
                block_class_name=None,
            ),
            FieldBlockContext.DETAILS: BlockConfig(
                has_block=self.has_details_block,
                block_class=self.details_block_class,
                block_class_name=None,
            ),
            FieldBlockContext.LIST_FILTERS: BlockConfig(
                has_block=self.has_list_filters_block,
                block_class=self.list_filters_block_class,
                block_class_name=None,
            ),
        }
        for context in FieldBlockContext:
            conf = self.config[context]
            if not conf.has_block:
                continue
        assert self.field_type is not None

    def is_disabled(self) -> bool:
        return all(not self.get_config(b).has_block for b in FieldBlockContext)

    if IS_WATCH:

        def get_report_formatter_class(self) -> type[ReportFieldFormatter] | None:
            if not self.has_report_block:
                return None
            if self.report_formatter_class:
                return _import(self.report_formatter_class)
            return None
    else:

        def get_report_formatter_class(self) -> type[ReportFieldFormatter] | None:
            return None

    def get_config(self, block_context: FieldBlockContext) -> BlockConfig:
        if block_context not in self.config:
            raise ValueError('Improperly initialized.')
        return self.config[block_context]

    def get_fixed_block_class[M: Model](self, block_context: FieldBlockContext) -> type[blocks.Block] | None:
        cfg = self.get_config(block_context)
        if not cfg.has_block or not cfg.block_class:
            return None

        if isinstance(cfg.block_class, str):
            return _import(cfg.block_class)
        if isclass(cfg.block_class) and issubclass(cfg.block_class, blocks.Block):
            return cfg.block_class

        assert callable(cfg.block_class)
        block_class = cfg.block_class()
        assert not isinstance(block_class, blocks.Block)
        assert issubclass(block_class, blocks.Block)
        return block_class

    def get_block_class_meta[M: Model](self, registry: ModelFieldRegistry[M], block_context: FieldBlockContext) -> type:
        model = registry.model
        meta_props: dict[str, Any] = {}
        label: StrOrPromise | None = None
        if self.custom_label:
            label = self.custom_label
        else:
            with suppress(FieldDoesNotExist):
                field = model._meta.get_field(self.field_name)
                if isinstance(field, Field):
                    label = field.verbose_name

        if label is None:
            # Fields need to be evaluated lazily, because when this function is called,
            # the model registry is not yet fully initialized.
            label = lazy_field_label(model, self.field_name)

        if block_context in (FieldBlockContext.REPORT, FieldBlockContext.DETAILS):
            formatter_cls = self.get_report_formatter_class()
            if formatter_cls:
                meta_props['report_value_formatter_class'] = formatter_cls

        meta_props['field_name'] = self.field_name
        return type('Meta', (), meta_props)


DEFAULT_FIELD_BASE_CLASSES: dict[str, type[blocks.Block[Any]]] = {
    FieldBlockContext.DASHBOARD: ColumnBlockBase,
    FieldBlockContext.REPORT: ContentBlockBase,
    FieldBlockContext.DETAILS: ContentBlockBase,
    FieldBlockContext.LIST_FILTERS: FilterBlockBase,
}

DEFAULT_BLOCK_SUFFIXES = {
    FieldBlockContext.DASHBOARD: 'ColumnBlock',
    FieldBlockContext.REPORT: 'Block',
    FieldBlockContext.DETAILS: 'Block',
    FieldBlockContext.LIST_FILTERS: 'FilterBlock',
}

REQUIRED_INTERFACES = {
    FieldBlockContext.DASHBOARD: (DashboardColumnInterface,),
    FieldBlockContext.REPORT: (FieldBlockMetaInterface, GeneralFieldBlockInterface),
    FieldBlockContext.DETAILS: (FieldBlockMetaInterface, GeneralFieldBlockInterface),
    FieldBlockContext.LIST_FILTERS: (FilterBlockInterface,),
}


@dataclass
class FieldContextConfig:
    context: FieldBlockContext
    enabled: bool = False
    block_base_class: type[blocks.Block[Any]] | None = None
    autogen_prefix: str | None = None
    block_suffix: str | None = None


def get_graphql_interfaces(block_class: type[blocks.Block[Any]]) -> list[type[graphene.Interface[Any]]] | None:
    gql_interfaces = getattr(block_class, 'graphql_interfaces', None)
    if gql_interfaces is None:
        return None
    for gql_interface in gql_interfaces:
        if not isclass(gql_interface):
            raise TypeError(f'GraphQL interface {gql_interface} of block class {block_class} is not a class')
        assert issubclass(gql_interface, graphene.Interface)
    return gql_interfaces


@dataclass
class ModelFieldRegistry[M: Model]:
    """
    A field registry initialized upon app initialization.

    It stores metadata about what features model's fields supports and provides
    the implemetations for various blocks derived from the fields.

    Currently used for Action and Indicator models.
    The features a field can support are:
        - Built-in-field customization such as visibility (plan-specific)  ??
        - Public site dashboard column blocks
        - Report spreadsheet column blocks
        - Block for the Action details page
    """

    model: type[M]
    target_module: ModuleType
    """The module to register the generated block classes to."""

    contexts: Iterable[FieldContextConfig] = field(default_factory=list, repr=False)
    """Configuration for the different field block contexts."""

    no_type_autogen: bool = False
    """Disable automatic generation of specific block classes for simple fields."""

    context_configs: dict[FieldBlockContext, FieldContextConfig] = field(default_factory=dict, repr=True)
    _registry: FieldRegistryDict = field(init=False, default_factory=dict, repr=False)

    _block_class_cache_by_name: dict[str, type[blocks.Block]] = field(init=False, default_factory=dict, repr=False)
    """Cache of generated block classes by block class name."""
    _block_class_cache_by_context: dict[FieldBlockContext, dict[str, type[blocks.Block]]] = field(
        init=False, default_factory=dict, repr=False
    )
    """Cache of generated block classes by context."""

    _field_id_enums: dict[FieldBlockContext, graphene.Enum] = field(init=False, default_factory=dict, repr=False)

    def _set_context_config(self, context: FieldBlockContext, conf: FieldContextConfig | None) -> None:
        if conf is None:
            conf = FieldContextConfig(context=context, enabled=False)
        else:
            conf = FieldContextConfig(**asdict(conf))
        if conf.block_base_class is None:
            conf.block_base_class = DEFAULT_FIELD_BASE_CLASSES[context]
        else:
            required_interfaces = REQUIRED_INTERFACES[context]
            self._validate_graphql_interfaces(conf.block_base_class, required_interfaces)
        if conf.autogen_prefix is None:
            default_prefix = self.model._meta.object_name
            conf.autogen_prefix = default_prefix
        if conf.block_suffix is None:
            conf.block_suffix = DEFAULT_BLOCK_SUFFIXES[context]
        self.context_configs[context] = conf

    def __post_init__(self):
        for context in FieldBlockContext:
            self._block_class_cache_by_context[context] = dict()

        # Set context configs with default fallbacks.
        conf_by_type = {conf.context: conf for conf in self.contexts}
        for context in FieldBlockContext:
            conf = conf_by_type.get(context)
            self._set_context_config(context, conf)

    def disable_fields(self, *fields: str) -> None:
        for name in fields:
            props = ModelFieldProperties(
                field_name=name,
                has_dashboard_column_block=False,
                has_report_block=False,
                has_details_block=False,
                has_list_filters_block=False,
            )
            self.register(props)

    def __getitem__(self, name: str) -> ModelFieldProperties:
        return self._registry[name]

    def __iter__(self) -> Iterator[ModelFieldProperties]:
        yield from self._registry.values()

    def register(self, props: ModelFieldProperties) -> None:
        if props.field_name in self._registry:
            msg = f'Trying to register {props.field_name} twice'
            raise ValueError(msg)
        self._registry[props.field_name] = props

    def finalize(self):
        fields_by_context: dict[FieldBlockContext, list[str]] = defaultdict(list)
        for name, props in self._registry.items():
            for context in FieldBlockContext:
                conf = props.get_config(context)
                if conf.has_block:
                    fields_by_context[context].append(name)

        for context, fields in fields_by_context.items():
            if len(fields) == 0:
                continue
            enum_name = f'{self.model._meta.object_name}{context.capitalize()}FieldName'
            enum_type = graphene.Enum(enum_name, {name.upper(): name for name in fields})
            self._field_id_enums[context] = enum_type

    def _validate_graphql_interfaces(
        self, block_class: type[blocks.Block], required_interfaces: Iterable[type[graphene.Interface[Any]]]
    ) -> None:
        gql_interfaces = get_graphql_interfaces(block_class)
        if gql_interfaces is None:
            raise TypeError(f'Block base class {block_class} does not have `graphql_interfaces` attribute.')

        for required_interface in required_interfaces:
            for gql_interface in gql_interfaces:
                if issubclass(gql_interface, required_interface):
                    break
            else:
                raise TypeError(f'Block base class {block_class} does not implement {required_interface}')

    def _validate_block_class(self, block_context: FieldBlockContext, block_class: type[blocks.Block]) -> None:
        base_class = self.context_configs[block_context].block_base_class
        assert base_class is not None
        block_class_interfaces = get_graphql_interfaces(block_class)
        if block_class_interfaces is None:
            raise TypeError(f'Block base class {block_class} does not have `graphql_interfaces` attribute.')
        self._validate_graphql_interfaces(block_class, block_class_interfaces)

    def _get_default_block_class_name(self, block_context: FieldBlockContext, field_name: str) -> str:
        conf = self.context_configs[block_context]
        camel_field = underscore_to_camelcase(field_name)
        assert conf.autogen_prefix is not None
        assert conf.block_suffix is not None
        class_name = f'{conf.autogen_prefix}{camel_field}{conf.block_suffix}'
        return class_name

    def _generate_block_class_for_field(
        self,
        block_context: FieldBlockContext,
        field_name: str,
        class_name: str,
    ) -> type[blocks.Block]:
        block_meta = self[field_name].get_block_class_meta(self, block_context)

        base_class = self.context_configs[block_context].block_base_class
        assert base_class is not None

        graphql_interfaces = get_graphql_interfaces(base_class)
        if graphql_interfaces is None:
            raise TypeError(f'Block base class {base_class} does not have `graphql_interfaces` attribute.')

        attrs: dict[str, Any] = {
            'Meta': block_meta,
            #'__module__': target_module,
            'graphql_interfaces': (FieldBlockMetaInterface, *graphql_interfaces),
        }

        graphql_fields = []
        super_fields = getattr(base_class, 'graphql_fields', None)
        if super_fields is not None:
            graphql_fields.extend(super_fields)

        if 'graphql_fields' not in attrs:
            attrs['graphql_fields'] = graphql_fields

        klass = type(class_name, (base_class,), attrs)
        setattr(self.target_module, class_name, klass)
        register_streamfield_block(klass)
        return klass

    def get_block_class(self, block_context: FieldBlockContext, field_name: str) -> type[blocks.Block]:
        cached = self._block_class_cache_by_context[block_context].get(field_name)
        if cached:
            return cached

        props = self[field_name]
        field_conf = props.get_config(block_context)
        if not field_conf.has_block:
            msg = f'No {block_context.value} block registered for {self.model}.{field_name}.'
            raise TypeError(msg)

        context_conf = self.context_configs[block_context]
        assert context_conf.block_base_class is not None

        # There might be a specialized block class for this field and context.
        fixed_class = props.get_fixed_block_class(block_context)
        if fixed_class is not None:
            self._validate_block_class(block_context, fixed_class)
            return fixed_class

        if self.no_type_autogen:
            block_base = context_conf.block_base_class
            assert block_base is not None
            return block_base

        class_name = field_conf.block_class_name or self._get_default_block_class_name(block_context, field_name)
        # A block class might be re-used in multiple contexts. In this case, we need to ensure
        # the cached class is a subclass of the context's base class.
        if cached_class := self._block_class_cache_by_name.get(class_name):
            context_sc = self.context_configs[block_context].block_base_class
            assert context_sc is not None
            if not issubclass(cached_class, context_sc):
                raise ValueError(f'Cached block class {cached_class} is not a subclass of {context_sc}')
            self._block_class_cache_by_context[block_context][field_name] = cached_class
            return cached_class

        block_class = self._generate_block_class_for_field(
            block_context,
            field_name,
            class_name,
        )
        self._block_class_cache_by_context[block_context][field_name] = block_class
        self._block_class_cache_by_name[class_name] = block_class
        return block_class

    def get_block(self, block_context: FieldBlockContext, field_name: str) -> blocks.Block:
        cls = self.get_block_class(block_context, field_name)
        kwargs: dict[str, Any] = {}
        if issubclass(cls, (ColumnBlockBase, GeneralFieldBlockBase)) or 'field_name' in cls.MUTABLE_META_ATTRIBUTES:
            kwargs['field_name'] = field_name
        formatter_cls = None
        if 'report_value_formatter_class' in cls.MUTABLE_META_ATTRIBUTES:
            formatter_cls = self[field_name].get_report_formatter_class()
            if formatter_cls:
                kwargs['report_value_formatter_class'] = formatter_cls

        block = cls(**kwargs)
        if IS_WATCH:
            # FIXME: Implement a base class for this in kausal-common later
            from actions.blocks.base import ActionReportContentField

            if isinstance(block, ActionReportContentField):
                formatter = block.report_value_formatter
                formatter.get_graphene_value_class()
        return block

    def get_field_enum_for_context(self, block_context: FieldBlockContext) -> graphene.Enum | None:
        return self._field_id_enums[block_context]


def sort_key(p: ModelFieldProperties) -> tuple[Any, Any, Any, Any, Any]:
    return (
        -1 if p.has_details_block else 1,
        -1 if p.has_dashboard_column_block else 1,
        -1 if p.has_report_block else 1,
        p.field_type,
        p.field_name,
    )


NOT_IMPLEMENTED = '○'
DEFAULT_IMPLEMENTATION = '●'
CUSTOM_IMPLEMENTATION = '❄'


def debug_registry(registry: ModelFieldRegistry[Any]):
    from rich.console import Console
    from rich.table import Table

    table = Table(
        'Field name',
        'Field type',
        'Details page',
        'Dashboard',
        'Reporting',
        'Custom formatter',
    )

    missing = set()

    for props in sorted(
        registry._registry.values(),
        key=sort_key,
    ):
        dashboard = report = details = NOT_IMPLEMENTED
        formatter = ''
        if props.has_dashboard_column_block:
            dashboard = DEFAULT_IMPLEMENTATION
        if props.dashboard_column_block_class:
            dashboard = CUSTOM_IMPLEMENTATION
        if props.has_report_block:
            report = DEFAULT_IMPLEMENTATION
        if props.report_block_class:
            report = CUSTOM_IMPLEMENTATION
        if props.has_details_block:
            details = DEFAULT_IMPLEMENTATION
        if props.details_block_class:
            details = CUSTOM_IMPLEMENTATION
        if props.report_formatter_class:
            formatter = CUSTOM_IMPLEMENTATION

        if all((x == NOT_IMPLEMENTED) for x in (dashboard, report, details)):
            missing.add(props.field_name)
            continue

        table.add_row(
            props.field_name,
            props.field_type,
            details,
            dashboard,
            report,
            formatter,
        )

    console = Console()
    console.print(table)
    console.print(
        textwrap.dedent(
            f"""
                {DEFAULT_IMPLEMENTATION} ───yes
                {NOT_IMPLEMENTED} ───no
                {CUSTOM_IMPLEMENTATION} ───custom implementation
            """,
        ),
    )
    console.print('\n', '\n    '.join(['No block implementations for:'] + sorted(missing)))
