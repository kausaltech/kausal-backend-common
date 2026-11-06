"""
Temporary workarounds for bugs in third-party mypy plugins.

Remove these patches once django-stubs and Pydantic defer generation of
methods whose generic type variables still contain placeholders.
"""

from pydantic.mypy import PydanticModelTransformer

from mypy.plugin import Plugin
from mypy.semanal_shared import has_placeholder
from mypy.types import Instance, TypeVarType
from mypy_django_plugin.lib import helpers
from mypy_django_plugin.transformers.models import ProcessManyToManyFields

_create_many_related_manager = ProcessManyToManyFields.create_many_related_manager


def _create_many_related_manager_after_through_is_resolved(
    self: ProcessManyToManyFields,
    model: Instance,
) -> None:
    """Prevent django-stubs from copying an unresolved ``_Through`` TypeVar."""
    through_type_var = self.many_related_manager.defn.type_vars[1]
    assert isinstance(through_type_var, TypeVarType)
    if has_placeholder(through_type_var):
        raise helpers.IncompleteDefnException()
    _create_many_related_manager(self, model)


ProcessManyToManyFields.create_many_related_manager = (  # type: ignore[method-assign]
    _create_many_related_manager_after_through_is_resolved
)

_transform_pydantic_model = PydanticModelTransformer.transform


def _transform_pydantic_model_after_type_vars_are_resolved(self: PydanticModelTransformer) -> bool:
    """Avoid copying unresolved generic bounds into generated method signatures."""
    if any(has_placeholder(type_var) for type_var in self._cls.info.defn.type_vars):
        if not self._api.final_iteration:
            self._api.defer()
        return False
    return _transform_pydantic_model(self)


PydanticModelTransformer.transform = (  # type: ignore[method-assign]
    _transform_pydantic_model_after_type_vars_are_resolved
)


class KausalMypyPlugin(Plugin):
    """Load Kausal-specific patches before semantic analysis starts."""


def plugin(_version: str) -> type[Plugin]:
    return KausalMypyPlugin
