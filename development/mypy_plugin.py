"""
Temporary workarounds for bugs in third-party mypy plugins.

Remove the patch below once django-stubs defers creation of related managers
whose ``_Through`` TypeVar still contains placeholders.
"""

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


class KausalMypyPlugin(Plugin):
    """Load Kausal-specific patches before semantic analysis starts."""


def plugin(_version: str) -> type[Plugin]:
    return KausalMypyPlugin
