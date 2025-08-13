from __future__ import annotations

from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib.admin.utils import unquote
from django.db import transaction
from django.db.models import ProtectedError
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, gettext_lazy, ngettext_lazy
from wagtail.snippets.views.snippets import DeleteView, IndexView

from kausal_common.const import IS_PATHS, IS_WATCH

from orgs.models import Organization

if IS_WATCH:
    from admin_site.utils import admin_req
    from admin_site.viewsets import WatchCreateView as CreateView, WatchEditView as EditView
elif IS_PATHS:
    from admin_site.viewsets import PathsCreateView as CreateView, PathsEditView as EditView, admin_req
else:
    raise RuntimeError('No admin views found')

if TYPE_CHECKING:
    from django.http import HttpRequest

    if IS_PATHS:
        from orgs.wagtail_hooks import OrganizationViewSet
    elif IS_WATCH:
        from orgs.wagtail_admin import OrganizationViewSet


class OrganizationViewMixin:
    request: HttpRequest

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()  # type: ignore[misc]
        obj = getattr(self, 'object', None)
        kwargs['parent_choices'] = Organization.get_parent_choices(obj=obj, user=admin_req(self.request).user)
        return kwargs


class CreateChildNodeView(OrganizationViewMixin, CreateView[Organization]):
    """
    View class that can take an additional URL param for parent id.

    Assumes that the url used to route to this view provides the primary key of
    the parent node as `parent_pk` attribute.
    """

    permission_required = 'add_child_node'

    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        self.parent_pk = unquote(kwargs['parent_pk'])
        self.parent_instance = get_object_or_404(self.get_queryset(), pk=self.parent_pk)
        return super().setup(request, *args, **kwargs)

    def user_has_permission(self, permission: str) -> bool:
        # A user can create an organization if they can edit *any* organization.
        # We just need to make sure that they can only create organizations that
        # are children of something they can edit.
        # TODO: Write tests to make sure we check in validation whether the user
        # has permissions depending on the chosen parent
        can_edit_parent = self.permission_policy.user_has_permission_for_instance(
            self.request.user, 'change', self.parent_instance
        )
        return can_edit_parent

    def get_page_subtitle(self):
        """Generate a title that explains you are adding a child."""
        return gettext_lazy('New child %(model)s for %(parent)s') % {
            'model': self.model._meta.verbose_name,
            'parent': self.parent_instance,
        }

    def get_initial(self):
        """Set the selected parent field to the parent_pk."""
        return {'parent': self.parent_pk}


class OrganizationCreateView(OrganizationViewMixin, CreateView):
    pass


class OrganizationEditView(OrganizationViewMixin, EditView):
    def user_has_permission(self, permission: str) -> bool:
        return self.permission_policy.user_has_permission_for_instance(admin_req(self.request).user, permission, self.object)


class Rollback(Exception):
    pass


def do_rollback():
    """
    Raise a Rollback exception.

    To be caught by the transaction.atomic() context manager to rollback the
    transaction.
    """
    raise Rollback()


class OrganizationDeleteView(DeleteView):
    def user_has_permission(self, permission: str) -> bool:
        return self.permission_policy.user_has_permission_for_instance(admin_req(self.request).user, permission, self.object)

    @property
    def confirmation_message(self):
        message = super().confirmation_message
        if not self.object:
            return message
        message += '\n' + _("This will delete the following objects:") + '\n'
        num_deleted_by_model = {}
        try:
            with transaction.atomic():
                num_deleted_by_model = self.object.delete()[1]
                do_rollback()
        except Rollback:
            pass
        except ProtectedError:
            # After confirming, the user will get an explanation why deletion didn't work
            return message
        items = []
        for model_identifier, num_deleted in num_deleted_by_model.items():
            model = apps.get_model(model_identifier)
            singular_str = "%(num_instances)d %(model_name_singular)s"
            plural_str = "%(num_instances)d %(model_name_plural)s"
            items.append(ngettext_lazy(singular_str, plural_str, num_deleted) % {
                'num_instances': num_deleted,
                'model_name_singular': model._meta.verbose_name,
                'model_name_plural': model._meta.verbose_name_plural,
            })
        message += ';\n'.join(items)
        return message


class OrganizationIndexView(IndexView[Organization]):
    # FIXME: in Wagtail 6.2.X this is the default, so this line can be deleted once we upgrade
    any_permission_required = ["add", "change", "delete", "view"]
    view_set: OrganizationViewSet | None = None
