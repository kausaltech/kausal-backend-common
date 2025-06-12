from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from generic_chooser.views import ModelChooserMixin, ModelChooserViewSet
from generic_chooser.widgets import AdminChooser

from users.models import User

from .models import Dataset

if TYPE_CHECKING:
    from django.http import HttpRequest


class DatasetChooserMixin(ModelChooserMixin):
    order_by: str | list[str]
    request: HttpRequest

    def get_unfiltered_object_list(self):
        user = self.request.user
        if not isinstance(user, User):  # could be anonymous or some unexpected implementation of AbstractBaseUser
            return Dataset.objects.none()
        objects = Dataset.permission_policy().instances_user_has_permission_for(user, 'view')
        if self.order_by:
            if isinstance(self.order_by, str):
                objects = objects.order_by(self.order_by)
            else:
                objects = objects.order_by(*self.order_by)
        return objects

    def user_can_create(self, user):
        return False


class DatasetChooserViewSet(ModelChooserViewSet):
    chooser_mixin_class = DatasetChooserMixin

    icon = 'kausal-dataset'
    model = Dataset
    page_title = _("Choose a dataset")
    per_page = 30


class DatasetChooser(AdminChooser):
    choose_one_text = _('Choose a dataset')
    choose_another_text = _('Choose another dataset')
    model = Dataset
    choose_modal_url_name = 'dataset_chooser:choose'
