from typing import Any, ClassVar

from django.db.models import Model
from django.utils.functional import cached_property as cached_property
from wagtail.admin.admin_url_finder import AdminURLFinder as AdminURLFinder
from wagtail.admin.ui import tables as tables
from wagtail.admin.utils import get_latest_str as get_latest_str
from wagtail.admin.widgets.button import HeaderButton as HeaderButton
from wagtail.models import DraftStateMixin as DraftStateMixin, ReferenceIndex as ReferenceIndex

from _typeshed import Incomplete

from .base import BaseListingView as BaseListingView, BaseObjectMixin as BaseObjectMixin
from .permissions import PermissionCheckedMixin as PermissionCheckedMixin

class TitleColumn(tables.TitleColumn):
    def get_link_attrs(self, instance, parent_context): ...

class UsageView[M: Model](PermissionCheckedMixin, BaseObjectMixin[M, Any], BaseListingView[M]):
    paginate_by: int
    usage_url_name: ClassVar[str | None]
    @cached_property
    def describe_on_delete(self): ...
    def get_edit_url(self, instance: M): ...
    def get_usage_url(self, instance: M): ...
    def get_context_data(self, *args, object_list: Incomplete | None = None, **kwargs): ...
