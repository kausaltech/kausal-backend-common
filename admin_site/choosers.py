from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from django.db.models import Model
from wagtail.admin.viewsets.chooser import ChooserViewSet as BaseChooserViewSet

if TYPE_CHECKING:
    from collections.abc import Iterable

    from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView, ChosenView, View


def inject_view(viewset_method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(viewset_method)
    def wrapped(self: Any, *args, **kwargs) -> Any:
        return viewset_method(self, *args, **kwargs)
    return wrapped

class ChooserViewSet[M: Model](BaseChooserViewSet):
    get_object_list: Callable[[ChooseView | ChooseResultsView], Iterable[M]]
    get_chosen_response_data: Callable[[ChosenView, M], dict[str, Any]]
    model: type[M]

    def inject_view_methods[VC: View](self, view_class: type[VC], method_names: list[str]) -> type[VC]:
        # We override this method to be able to pass the request to the methods.
        viewset = self
        overrides = {}
        for method_name in method_names:
            viewset_method = getattr(viewset, method_name, None)
            if viewset_method is None:
                continue

            overrides[method_name] = inject_view(viewset_method)

        if overrides:
            return type(view_class.__name__, (view_class,), overrides)  # pyright: ignore[reportReturnType]
        return view_class

    @property
    def chosen_view(self):
        view_class = self.inject_view_methods(self.chosen_view_class, ["get_chosen_response_data"])
        return self.construct_view(view_class)
