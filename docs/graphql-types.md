# Writing GraphQL Types (Strawberry + strawberry-django)

This is the working playbook for adding new types to the Strawberry side
of the schema. It applies to both Kausal Paths and Kausal Watch backends
— if you're tempted to deviate, update this doc instead.

## Prefer `@strawberry_django.type` over plain `@sb.type` for ORM-backed types

If the type wraps a Django model, reach for `@strawberry_django.type`
first. It pays off in three places:

1. **No `from_model` boilerplate.** Resolvers and parent fields can
   return the Django model instance directly — `strawberry_django` lists
   the model class in `is_type_of`, so model instances satisfy the
   schema's `T` type.
2. **`auto` field declarations** eliminate per-field
   `field=model.field` plumbing for the bread-and-butter scalars.
3. **Free FK resolution** when the related model also has a
   `@strawberry_django.type`. Just annotate
   `created_by: UserType | None` and you're done — no resolver method.

A typical type looks like this:

```python
from typing import TYPE_CHECKING, Annotated

import strawberry as sb
import strawberry_django
from strawberry import auto

from kausal_common.datasets.models import DataPointComment as DataPointCommentModel

if TYPE_CHECKING:
    from users.schema import UserType


@strawberry_django.type(DataPointCommentModel, name='DataPointComment')
class DataPointCommentType:
    text: auto
    is_sticky: auto
    review_state: auto
    resolved_at: auto
    resolved_by: Annotated['UserType', sb.lazy('users.schema')] | None
    created_at: auto
    created_by: Annotated['UserType', sb.lazy('users.schema')] | None

    @strawberry_django.field
    @staticmethod
    def id(root: sb.Parent[DataPointCommentModel]) -> sb.ID:
        return sb.ID(str(root.uuid))
```

The `id` field deserves a custom resolver: every type should expose
`id`, but we never expose Django primary keys over GraphQL. Resolve `id`
to the row's `uuid` instead, and don't add a separate `uuid` field —
clients shouldn't have to choose.

## `graphql_type=` vs return-type annotation: never use `Any`

When you can't (or don't want to) line up the Python annotation and the
GraphQL type — e.g. the resolver returns a Django model but the schema
should expose a Strawberry type, or you need a lazy/forward-referenced
type that the type checker can't see at definition time — use the
`graphql_type=` keyword to pin the schema side. **The Python annotation
should still be the most specific real type you can write.** `-> Any` is
a smell. The same applies to casting the return type to a different type —
generally it should be avoided.

```python
# Good: Python annotation says what we actually return; graphql_type
# tells Strawberry what the schema sees.
@sb.field(graphql_type=UserType | None)
@staticmethod
def me(info: gql.Info) -> User | None:
    return user_or_none(info.context.user)

# Bad: `Any` throws away type information for no reason.
@sb.field(graphql_type=UserType | None)
@staticmethod
def me(info: gql.Info) -> Any:  # NO
    return user_or_none(info.context.user)
```

For class-attribute fields the same principle applies — the annotation
on the class is the *Python* type; `graphql_type=` on the descriptor
overrides what the schema reports.

## Lazy / cross-module type references

When a type from another module would cause a circular import, put the
import behind `TYPE_CHECKING` and use `Annotated[..., sb.lazy(...)]`
with a quoted forward reference. Strawberry resolves the lazy
annotation at schema-build time.

```python
if TYPE_CHECKING:
    from users.schema import UserType


@sb.type
class FoobarType:
    resolved_by: Annotated['UserType', sb.lazy('users.schema')] | None
```

Two things to keep in mind:

- The forward reference (`'UserType'`) **must** be quoted. Without
  quotes, Python will try to resolve `UserType` at module-import time
  and fail.
- The `TYPE_CHECKING` import gives the type checker visibility. The
  `sb.lazy(...)` call gives Strawberry the runtime module path for the
  delayed import.

## Choices fields and enums: prefer `TextChoicesField`

`strawberry_django` has first-class support for
[django-choices-field](https://github.com/bellini666/django-choices-field).
When a model field uses `TextChoicesField(choices_enum=MyEnum)`,
declaring the field as `my_field: auto` is enough — Strawberry
auto-decorates `MyEnum` with `@strawberry.enum` and generates the GraphQL
enum from it. The same `MyEnum` class is then usable as the input type in
mutation inputs, so you have **one canonical enum** on both sides.

A plain `models.CharField(choices=MyEnum.choices)` does *not* get the
same treatment. If you find yourself writing a separate
`@strawberry.enum` class plus a hand-rolled resolver to map the model
string to the schema enum, **stop and ask** whether the underlying
model field should be migrated to `TextChoicesField`.

When the migration is the right move, follow this recipe:

1. Move the `TextChoices` subclass to module level (rename if needed)
   so the enum has a stable, importable identity. Keep a class-level
   alias for backwards compatibility:

   ```python
   class DataPointCommentReviewState(models.TextChoices):
       RESOLVED = 'resolved', _('Resolved')
       UNRESOLVED = 'unresolved', _('Unresolved')


   class DataPointComment(...):
       ReviewState = DataPointCommentReviewState  # bw compat alias
       review_state = TextChoicesField(
           choices_enum=DataPointCommentReviewState,
           null=True,
           blank=True,
       )
   ```

2. `TextChoicesField` rejects non-choice values; if the previous
   `CharField` used `blank=True` with `''` as the not-applicable
   sentinel, you need `null=True` on the new field **and** a data
   migration converting legacy `''` rows to `NULL`:

   ```python
   def empty_string_to_null(apps, schema_editor):
       Model = apps.get_model('app', 'Model')
       Model.objects.filter(field='').update(field=None)

   operations = [
       migrations.AlterField(...),
       migrations.RunPython(empty_string_to_null, reverse_code=null_to_empty_string),
   ]
   ```

3. On the GraphQL side, drop the manual enum and the mapping resolver.
   `field: auto` is now sufficient; mutation inputs reference the
   `TextChoices` class directly.

**Ask before touching shared models.** If the model lives in
`kausal_common` (i.e. shared with Watch), surface the proposed change
to the user before editing — these refactors look small but they ripple
across two products. If a refactor leads to cleaner code (e.g. less repetition,
more elegant architecture, fewer source lines) it probably is the better way.

## Ruff and runtime-evaluated annotations

Strawberry and `strawberry_django` evaluate annotations at runtime (the
decorator inspects the class body to build the schema). Ruff's
`TC001`/`TC002`/`TC003` family wants to move imports used only in
annotations into `TYPE_CHECKING` blocks. For Strawberry types that
breaks the world: `auto`, ORM enum classes, etc. need to be present at
runtime so the decorator can resolve them.

The fix is in `kausal_common/configs/ruff.toml` under
`[lint.flake8-type-checking]`:

```toml
runtime-evaluated-decorators = [
  "strawberry.type",
  "strawberry.input",
  "strawberry_django.type",
  "strawberry_django.input",
  # ...
]
```

If you introduce a new Strawberry-family decorator (custom mutation
helper, pydantic adapter, …) and ruff starts demanding `TYPE_CHECKING`
moves that would break the schema, **add the decorator path to that
list** instead of papering over with per-file `# noqa: TC00x`. The
master list is authoritative — if a tool is missing, that's the bug.

If you have an oddball case where the runtime evaluation only matters
for a single import (e.g. `from strawberry import auto`), a targeted
`# noqa: TC002` is acceptable, but check the master list first.

## Don't use `from __future__ import annotations` in files defining Strawberry types

PEP 563 makes every annotation a string. `sb.Private['SomeModel | None']`
relies on those annotations being evaluable at schema-build time — with
`from __future__ import annotations`, references that were resolvable
only inside a `TYPE_CHECKING` block become unresolvable strings and
Strawberry will raise `UnresolvedFieldTypeError`.

If you need the future-import for some other reason, audit every
`sb.Private[...]` and lazy annotation in the file to make sure the
referenced names are importable at runtime.
