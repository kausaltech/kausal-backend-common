from __future__ import annotations

import types
from abc import ABC
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeAliasType, cast, get_args, overload

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise
from django.utils.translation import (
    get_language as get_language,  # noqa: PLC0414
    gettext as gettext,  # noqa: PLC0414
    gettext_lazy as gettext_lazy,  # noqa: PLC0414
)
from django_stubs_ext import StrPromise
from pydantic import BaseModel, ConfigDict
from pydantic_core import core_schema

from loguru import logger

from kausal_common.i18n.helpers import convert_language_code
from kausal_common.strawberry.pydantic import register_type_conversion

if TYPE_CHECKING:
    from collections.abc import Iterable
    from contextvars import Token

    from django.db.models import Model
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema


SUPPORTED_LANGUAGES: set[str] | None
DEFAULT_LANGUAGE: str | None

try:
    SUPPORTED_LANGUAGES = {x[0] for x in settings.LANGUAGES}
    DEFAULT_LANGUAGE = settings.LANGUAGE_CODE
except ImproperlyConfigured:
    SUPPORTED_LANGUAGES = None
    DEFAULT_LANGUAGE = None


NO_DEFAULT_LANGUAGE_MSG = 'No default language found'
I18N_CONTEXT_MISSING_MSG = 'I18n context not set. Did you remember to set_i18n_context()?'


class I18nContextMissingError(Exception):
    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            super().__init__(I18N_CONTEXT_MISSING_MSG)
        else:
            super().__init__(*args, **kwargs)


class DefaultLanguageNotProvidedError(Exception):
    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            super().__init__(NO_DEFAULT_LANGUAGE_MSG)
        else:
            super().__init__(*args, **kwargs)


type LazyStrArgs = tuple[tuple[Any, ...], dict[str, Any]]


class TranslatedString:
    _i18n: dict[str, str]
    default_language: str | None
    _lazy_source: Promise | None = None

    @overload
    def __init__(self, lazy_str: Promise, /): ...

    @overload
    def __init__(self, *args: str, default_language: str | None = None, **kwargs: str): ...

    def __init__(self, *args: str | Promise, default_language: str | None = None, **kwargs: str):
        self._i18n = {}

        if default_language is None:
            default_language = get_default_language()

        if len(args) > 1:
            raise Exception('You can supply at most one default translation')
        if len(args) == 1:
            if isinstance(args[0], Promise):
                self._lazy_source = args[0]
                self.default_language = None
                return

            # For a plain string, we require the default language from context.
            if not default_language:
                raise DefaultLanguageNotProvidedError()
            default_language = convert_language_code(default_language, 'iso')
            self._i18n[default_language] = args[0]
        elif len(kwargs) == 1:
            default_language = next(iter(kwargs.keys()))
        elif default_language:
            default_language = convert_language_code(default_language, output_format='iso')

        i18n = {convert_language_code(key, 'iso'): value for key, value in kwargs.items()}

        self.default_language = default_language
        self._i18n.update(i18n)

    @staticmethod
    def lazy_in_lang(lazy_str: LazyStrArgs, lang: str) -> str:
        from django.utils import translation
        from django.utils.translation import trans_real

        # We extract the arguments and keyword arguments from the lazy string.
        lazy_kwargs = cast('dict[str, Any]', getattr(lazy_str, '_kw'))  # noqa: B009
        lazy_args = cast('tuple[Any, ...]', getattr(lazy_str, '_args'))  # noqa: B009
        assert not lazy_args
        assert len(lazy_kwargs) == 1
        lang = convert_language_code(lang, 'django')
        with translation.override(lang):
            real_catalog = cast('Any', trans_real.catalog())
            key = lazy_args[0]
            s = real_catalog.get(key)
            if s is None and lang.startswith('en'):
                return key
        return s

    @cached_property
    def _i18n_from_lazy(self) -> dict[str, str]:
        """
        Evaluate the lazy string for all globally supported languages.

        Cached so that repeated access is cheap. The ``i18n`` property
        filters this down to the active context's languages.
        """
        from django.utils import translation

        assert self._lazy_source is not None
        if SUPPORTED_LANGUAGES is None:
            raise I18nContextMissingError()
        ret: dict[str, str] = {}
        for lang in SUPPORTED_LANGUAGES:
            with translation.override(convert_language_code(lang, 'django')):
                ret[lang] = str(self._lazy_source)
        return ret

    @property
    def i18n(self) -> dict[str, str]:
        if self._lazy_source is not None:
            all_translations = self._i18n_from_lazy
            ctx = get_i18n_context()
            if ctx is not None:
                return {lang: val for lang, val in all_translations.items() if lang in ctx.all_languages}
            return all_translations
        return self._i18n

    @classmethod
    def from_lazy_string(cls, lazy_str: Promise) -> Self:
        return cls(lazy_str)

    def get_fallback(self) -> str:
        default_language = self.default_language or get_default_language()
        if default_language is None:
            raise DefaultLanguageNotProvidedError()
        dl = default_language
        if dl in self.i18n:
            return self.i18n[dl]
        if '-' in dl:
            lang, _ = dl.split('-')
            if lang in self.i18n:
                return self.i18n[lang]
        raise Exception('Default translation not available for: %s' % self.default_language)

    def t(self, lang: str) -> str | None:
        """Get the translation for a specific language code, or None if not available."""
        lang = convert_language_code(lang, 'iso')
        return self.i18n.get(lang)

    def all(self) -> list[str]:
        unique_vals = set(self.i18n.values())
        return list(unique_vals)

    def set_modeltrans_field(self, obj: Model, field_name: str, default_language: str):
        field_val, i18n = get_modeltrans_attrs_from_str(self, field_name, default_lang=default_language)
        setattr(obj, field_name, field_val)

        old_i18n: dict[str, str] = dict(getattr(obj, 'i18n') or {})  # noqa: B009
        old_i18n.update(i18n)
        setattr(obj, 'i18n', old_i18n)  # noqa: B010

    def __str__(self):
        try:
            lang = get_language()
        except Exception:
            lang = None

        if lang:
            lang = convert_language_code(lang, 'iso')

        if lang not in self.i18n:
            ret = self.get_fallback()
        else:
            ret = self.i18n[lang]
        return ret

    def __repr__(self):
        return "[i18n]'%s'" % str(self)

    @classmethod
    def __get_validators__(cls):  # noqa: ANN206
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> Self:
        from django.utils.functional import Promise

        if isinstance(v, Promise):
            return cls.from_lazy_string(v)
        if isinstance(v, str):
            default_language = get_default_language()
            if default_language is None:
                # Bare strings without an I18nContext come from legacy compact-serialized
                # JSON (before we switched to always serializing as dicts). Assume 'en'
                # so existing data can be deserialized; resync will convert to dict format.
                default_language = 'en'
            return cls(v, default_language=default_language)
        if isinstance(v, TranslatedString):
            # FIXME: Check the current i18n context and convert the languages if needed.
            return cls(default_language=v.default_language, **v.i18n)
        if not isinstance(v, dict):
            raise TypeError('TranslatedString expects dict, str, or TranslatedString, not %s' % type(v))
        languages = list(v.keys())
        if 'default_language' in languages:
            languages.remove('default_language')
        if SUPPORTED_LANGUAGES:
            for lang in languages:
                if lang not in SUPPORTED_LANGUAGES:
                    raise ValueError('unsupported language: %s' % lang)
        return cls(**v)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        def validate_value(v: Any) -> TranslatedString:
            return cls.validate(v)

        def serialize(ts: TranslatedString) -> dict[str, str]:
            """Serialize as a dict so round-tripping does not require an I18nContext."""
            return dict(ts.i18n)

        from_str_schema = core_schema.chain_schema([
            core_schema.str_schema(),
            core_schema.no_info_plain_validator_function(validate_value),
        ])
        from_dict_schema = core_schema.chain_schema([
            core_schema.dict_schema(core_schema.str_schema(), core_schema.str_schema()),
            core_schema.no_info_plain_validator_function(validate_value),
        ])
        return core_schema.json_or_python_schema(
            json_schema=core_schema.union_schema([
                from_str_schema,
                from_dict_schema,
            ]),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(cls),
                from_str_schema,
                from_dict_schema,
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize,
            ),
        )


def get_modeltrans_attrs_from_str(
    s: str | TranslatedString, field_name: str, default_lang: str, strict: bool = True
) -> tuple[str, dict[str, str]]:
    i18n = {}
    default_lang = convert_language_code(default_lang, 'iso')

    if isinstance(s, TranslatedString):
        translations = {
            f'{field_name}_{convert_language_code(lang, "modeltrans")}': v for lang, v in s.i18n.items() if lang != default_lang
        }
        i18n.update(translations)

        if default_lang not in s.i18n:
            fallbacks = settings.MODELTRANS_FALLBACK.get(convert_language_code(default_lang, 'django'), ())
            for lang in fallbacks:
                lang_iso = convert_language_code(lang, 'iso')
                if lang_iso in s.i18n:
                    key = f'{convert_language_code(default_lang, "modeltrans")}_{convert_language_code(lang, "modeltrans")}'
                    i18n[key] = s.i18n[lang_iso]
                    break
            else:
                if strict:
                    raise Exception("Field '%s' does not have a value in language %s (%s)" % (field_name, default_lang, s.i18n))
                logger.warning("Field '%s' does not have a value in language %s (%s)", field_name, default_lang)
                s.i18n[default_lang] = ''

        field_val = s.i18n[default_lang]
    else:
        field_val = s

    return field_val, i18n


def get_translated_string_from_modeltrans(
    obj: Model,
    field_name: str,
    primary_language: str,
) -> TranslatedString:
    val = getattr(obj, field_name)
    langs = {}
    langs[primary_language] = val
    i18n: dict[str, str] = obj.i18n or {}  # type: ignore
    for key, val in i18n.items():
        parts = key.split('_')
        lang = parts.pop(-1)
        field = '_'.join(parts)
        if field != field_name:
            continue
        langs[lang] = val
    return TranslatedString(default_language=primary_language, **langs)


type I18nStringInstance = TranslatedString | str
type I18nString = I18nStringInstance | StrPromise


class I18nContext:
    default_language: str
    other_languages: set[str]

    __slots__ = ('default_language', 'other_languages')

    def __init__(self, default_language: str, other_languages: Iterable[str]):
        self.default_language = convert_language_code(default_language, 'iso')
        other_languages = {convert_language_code(lang, 'iso') for lang in other_languages}
        other_languages.discard(self.default_language)
        self.other_languages = other_languages

    @property
    def all_languages(self) -> list[str]:
        """Return all supported languages with the default language first."""
        return [self.default_language, *self.other_languages]


i18n_context: ContextVar[I18nContext | None] = ContextVar('i18n_default_language', default=None)


@contextmanager
def set_i18n_context(lang: str, other_languages: Iterable[str]):
    token = i18n_context.set(I18nContext(lang, other_languages))
    try:
        yield
    finally:
        i18n_context.reset(token)


def get_i18n_context() -> I18nContext | None:
    return i18n_context.get()


def get_default_language() -> str | None:
    ctx = i18n_context.get()
    if ctx is None:
        return None
    return ctx.default_language


def get_other_supported_languages() -> set[str] | None:
    ctx = i18n_context.get()
    if ctx is None:
        return None
    return ctx.other_languages


_module_init_context_token: Token[I18nContext | None] | None = i18n_context.set(I18nContext('en', []))

is_query_with_instance_context: ContextVar[bool | None] = ContextVar('is_query_with_instance_context', default=None)


def on_app_ready():
    global _module_init_context_token  # noqa: PLW0603

    if _module_init_context_token is None:
        return
    i18n_context.reset(_module_init_context_token)
    _module_init_context_token = None


def validate_translated_string(cls: type[BaseModel], field_name: str, obj: dict[str, Any]) -> TranslatedString | None:  # noqa: C901, PLR0912
    f = cls.model_fields[field_name]
    field_val = obj.get(field_name)
    langs: dict[str, str] = {}
    default_language = get_default_language()

    if isinstance(field_val, TranslatedString):
        return field_val

    if isinstance(field_val, str):
        assert default_language is not None
        langs[default_language] = field_val
    elif isinstance(field_val, dict):
        return TranslatedString(**field_val)
    else:
        if default_language is None:
            raise Exception('default_language is None')
        if field_val is not None:
            raise TypeError('%s: Invalid type: %s' % (field_name, type(field_val)))

    base_default = default_language.split('-')[0]

    # FIXME: how to get default language?
    for key, val in list(obj.items()):
        if '_' not in key or not key.startswith(field_name):
            continue
        parts = key.split('_')
        lang = parts.pop(-1)
        fn = '_'.join(parts)
        if fn != field_name:
            continue
        if not isinstance(val, str):
            raise TypeError('%s: Expecting str, got %s' % (key, type(val)))
        obj.pop(key)
        if lang == base_default:
            lang = default_language
        langs[lang] = val

    if not langs:
        if not f.is_required():
            return None
        raise KeyError('%s: Value missing' % field_name)
    ts = TranslatedString(default_language=default_language, **langs)
    return ts


type FieldAnnotation = type[Any] | TypeAliasType | types.UnionType | None


def is_i18n_field(type_: FieldAnnotation) -> bool:
    if type_ is TranslatedString:
        return True
    if isinstance(type_, TypeAliasType):
        type_ = type_.__value__
    if isinstance(type_, types.UnionType):
        for arg in get_args(type_):
            if is_i18n_field(arg):
                return True
    return False


def _get_i18n_model_type(annotation: FieldAnnotation) -> type[I18nBaseModel] | None:
    """If *annotation* is (or wraps a list of) an I18nBaseModel subclass, return it."""
    if isinstance(annotation, type) and issubclass(annotation, I18nBaseModel):
        return annotation
    if isinstance(annotation, TypeAliasType):
        return _get_i18n_model_type(annotation.__value__)
    if isinstance(annotation, types.UnionType):
        for arg in get_args(annotation):
            result = _get_i18n_model_type(arg)
            if result is not None:
                return result
    return None


def _get_list_item_i18n_model(annotation: FieldAnnotation) -> type[I18nBaseModel] | None:
    """If *annotation* is ``list[SomeI18nBaseModel]``, return the item type."""
    origin = getattr(annotation, '__origin__', None)
    if origin is not list:
        return None
    args = get_args(annotation)
    if not args:
        return None
    return _get_i18n_model_type(args[0])


class I18nBaseModel(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    __i18n_fields__: ClassVar[set[str]]
    __i18n_nested_fields__: ClassVar[dict[str, type[I18nBaseModel]]]
    __i18n_nested_list_fields__: ClassVar[dict[str, type[I18nBaseModel]]]

    @classmethod
    def __pydantic_on_complete__(cls) -> None:
        cls.__i18n_fields__ = set()
        cls.__i18n_nested_fields__ = {}
        cls.__i18n_nested_list_fields__ = {}
        for fn, f in cls.model_fields.items():
            if is_i18n_field(f.annotation):
                cls.__i18n_fields__.add(fn)
                continue
            nested = _get_i18n_model_type(f.annotation)
            if nested is not None:
                cls.__i18n_nested_fields__[fn] = nested
                continue
            list_nested = _get_list_item_i18n_model(f.annotation)
            if list_nested is not None:
                cls.__i18n_nested_list_fields__[fn] = list_nested

    @classmethod
    def from_yaml_config(cls, config: dict[str, Any]) -> Self:
        """Validate from a YAML-style dict where translated fields use ``name_en`` suffixes."""
        config = config.copy()
        for fn in cls.__i18n_fields__:
            config[fn] = validate_translated_string(cls, fn, config)
        for fn, model_cls in cls.__i18n_nested_fields__.items():
            val = config.get(fn)
            if isinstance(val, dict):
                config[fn] = model_cls.from_yaml_config(val)
        for fn, model_cls in cls.__i18n_nested_list_fields__.items():
            val = config.get(fn)
            if isinstance(val, list):
                config[fn] = [model_cls.from_yaml_config(item) if isinstance(item, dict) else item for item in val]
        return cls.model_validate(config)


for cls in (I18nString, I18nStringInstance, TranslatedString):
    register_type_conversion(cls, str)
