from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeGuard

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import ManyToManyRel, Model
from django.db.models.fields.related import RelatedField
from django.db.models.fields.reverse_related import ForeignObjectRel
from modeltrans.fields import TranslatedVirtualField

from rich.console import RenderableType, group
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from django.db.models.fields import Field


@dataclass
class GroupedFields:
    model: type[Model]
    related_fields: list[RelatedField] = field(default_factory=list, init=False)
    reverse_fields: list[ForeignObjectRel] = field(default_factory=list, init=False)
    gfk_fields: list[GenericForeignKey] = field(default_factory=list, init=False)
    plain_fields: list[Field] = field(default_factory=list, init=False)
    related_models: set[type[Model]] = field(default_factory=set, init=False)

    def __post_init__(self):
        meta = self.model._meta
        for f in sorted(meta.get_fields(), key=lambda f: (str(type(f).__name__), f.name)):
            if isinstance(f, RelatedField):
                self.related_fields.append(f)
            elif isinstance(f, ForeignObjectRel):
                self.reverse_fields.append(f)
            elif isinstance(f, GenericForeignKey):
                self.gfk_fields.append(f)
            elif isinstance(f, TranslatedVirtualField):
                continue
            else:
                self.plain_fields.append(f)
        self.related_models = self._get_related_models()

    def _get_related_models(self) -> set[type[Model]]:
        related_models = set[type[Model]]()
        for f in self.related_fields:
            if f.related_model == 'self':
                continue
            related_models.add(f.related_model)
        for rev_field in self.reverse_fields:
            if isinstance(rev_field, ManyToManyRel) and rev_field.through is not None:
                related_models.add(rev_field.through)
            if rev_field.related_model == 'self':
                continue
            related_models.add(rev_field.related_model)
        return related_models


class TreeWalker:
    models_to_skip: set[type[Model]]
    walked_models: set[type[Model]] = set()
    model: type[Model]

    def check_relation(self, model: type[Model], field: ForeignObjectRel | RelatedField) -> bool | None:
        # Implement in subclasses
        return None

    def __init__(self, model: type[Model], models_to_skip: Iterable[type[Model]] | None = None):
        self.models_to_skip = set(models_to_skip or [])
        self.walked_models = set()
        self.walked_models.update(self.models_to_skip)
        self.model = model

    def should_skip(self, model: type[Model]) -> bool:
        for skip_model in self.models_to_skip:  # noqa: SIM110
            if issubclass(model, skip_model):
                return True
        return False

    def should_walk(self, model: type[Model] | Literal['self']) -> TypeGuard[type[Model]]:
        if model == 'self':
            return False
        if self.should_skip(model):
            return False
        return model in self.walked_models

    def field_name(self, field: Field | ForeignObjectRel) -> Text:
        if isinstance(field, ForeignObjectRel):
            is_ok = self.check_relation(field.model, field)
        else:
            is_ok = None
        parts: list[str | Text] = [Text(field.name, style='inspect.attr')]
        if is_ok is not None:
            parts = ['✅' if is_ok else '❌', ' ', *parts]
        return Text.assemble(*parts)

    def field_type(self, field: Field | ForeignObjectRel) -> Text:
        return Text(type(field).__name__, style='inspect.class')

    def model_name(self, model: type[Model]) -> Text:
        return Text(model._meta.label, style='repr.call')

    def related_model_name(self, field: RelatedField | ForeignObjectRel) -> Text:
        m = field.related_model
        if m == 'self' or field.model is m:
            return Text('self', style='green')
        return self.model_name(m)

    def walk_related_fields(self, tree: Tree, fields: GroupedFields, models_to_walk: set[type[Model]]):
        for rel_field in fields.related_fields:
            related_model = rel_field.related_model
            parent = tree.add(self.related_field_leaf(rel_field))
            if related_model == 'self':
                continue
            if related_model not in models_to_walk or self.should_skip(related_model):
                continue
            models_to_walk.remove(related_model)
            self.walk_related_model(related_model, parent)

    def walk_reverse_fields(self, tree: Tree, fields: GroupedFields, models_to_walk: set[type[Model]]):
        for rev_field in fields.reverse_fields:
            parent = tree.add(self.reverse_field_leaf(rev_field))
            related_model = rev_field.related_model
            if isinstance(rev_field, ManyToManyRel) and rev_field.through is not None:
                related_model = rev_field.through
            if related_model == 'self' or related_model not in models_to_walk or self.should_skip(related_model):
                continue
            models_to_walk.remove(related_model)
            self.walk_related_model(related_model, parent)

    def walk_related_model(self, model: type[Model], parent: Tree):
        tree = parent.add(self.model_name(model))
        grouped_fields = GroupedFields(model)
        models_to_walk = set(grouped_fields.related_models) - self.walked_models
        self.walked_models.update(models_to_walk)
        self.walk_related_fields(tree, grouped_fields, models_to_walk)
        self.walk_reverse_fields(tree, grouped_fields, models_to_walk)

    def related_field_leaf(self, field: RelatedField | ForeignObjectRel) -> Text:
        return Text.assemble(
            self.field_name(field),
            ' (',
            self.field_type(field),
            ')',
            ' -> ',
            self.related_model_name(field),
        )

    def reverse_field_leaf(self, field: ForeignObjectRel) -> Text:
        remote_field = field.remote_field
        return Text.assemble(
            self.field_name(field),
            ' (',
            self.field_type(field),
            ') <- ',
            self.related_model_name(field),
            '.',
            self.field_name(remote_field),
            ' (',
            self.field_type(remote_field),
            ')',
        )

    @group()
    def walk(self) -> Generator[RenderableType, None, None]:
        meta = self.model._meta
        table = Table(title=f'{meta.label}', title_justify='left')
        grouped_fields = GroupedFields(self.model)
        table.add_column('Field')
        table.add_column('Type')
        for f in grouped_fields.plain_fields:
            table.add_row(self.field_name(f), self.field_type(f))

        yield table

        self.walked_models.add(self.model)

        models_to_walk = set(grouped_fields.related_models) - self.walked_models
        self.walked_models.update(models_to_walk)

        tree = Tree('Related fields')
        self.walk_related_fields(tree, grouped_fields, models_to_walk)
        yield tree

        tree = Tree('Reverse fields')
        self.walk_reverse_fields(tree, grouped_fields, models_to_walk)
        yield tree
