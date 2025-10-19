from collections.abc import Iterable

from django.contrib.auth.models import Permission
from django.db.models import Model, QuerySet
from django.utils.functional import cached_property
from wagtail.models import Page

from users.models import User

class PermissionHelper[M: Model]:
    """
    Provides permission-related helper functions to help determine what a
    user can do with a 'typical' model (where permissions are granted
    model-wide), and to a specific instance of that model.
    """
    def __init__(self, model: type[M], inspect_view_enabled: bool = ...) -> None:
        ...

    def get_all_model_permissions(self) -> QuerySet[Permission, Permission]:
        """
        Return a queryset of all Permission objects pertaining to the `model`
        specified at initialisation.
        """

    @cached_property
    def all_permission_codenames(self) -> Iterable[str]:
        ...

    def get_perm_codename(self, action: str) -> str:
        ...

    def user_has_specific_permission(self, user, perm_codename: str) -> bool:
        """
        Combine `perm_codename` with `self.opts.app_label` to call the provided
        Django user's built-in `has_perm` method.
        """

    def user_has_any_permissions(self, user: User) -> bool:
        """
        Return a boolean to indicate whether `user` has any model-wide
        permissions
        """

    def user_can_list(self, user: User) -> bool:
        """
        Return a boolean to indicate whether `user` is permitted to access the
        list view for self.model
        """

    def user_can_create(self, user: User) -> bool:
        """
        Return a boolean to indicate whether `user` is permitted to create new
        instances of `self.model`
        """

    def user_can_inspect_obj(self, user: User, obj: M) -> bool:
        """
        Return a boolean to indicate whether `user` is permitted to 'inspect'
        a specific `self.model` instance.
        """
        ...

    def user_can_edit_obj(self, user: User, obj: M) -> bool:
        """
        Return a boolean to indicate whether `user` is permitted to 'change'
        a specific `self.model` instance.
        """

    def user_can_delete_obj(self, user: User, obj: M) -> bool:
        """
        Return a boolean to indicate whether `user` is permitted to 'delete'
        a specific `self.model` instance.
        """
        ...

    def user_can_unpublish_obj(self, user: User, obj: M) -> bool:
        ...

    def user_can_copy_obj(self, user: User, obj: M) -> bool:
        ...



class PagePermissionHelper(PermissionHelper[Page]):
    """
    Provides permission-related helper functions to help determine what
    a user can do with a model extending Wagtail's Page model. It differs
    from `PermissionHelper`, because model-wide permissions aren't really
    relevant. We generally need to determine permissions on an
    object-specific basis.
    """
    def get_valid_parent_pages(self, user): # -> QuerySet[Page, Page]:
        """
        Identifies possible parent pages for the current user by first looking
        at allowed_parent_page_models() on self.model to limit options to the
        correct type of page, then checking permissions on those individual
        pages to make sure we have permission to add a subpage to it.
        """
        ...

    def user_can_list(self, user): # -> Literal[True]:
        """
        For models extending Page, permitted actions are determined by
        permissions on individual objects. Rather than check for change
        permissions on every object individually (which would be quite
        resource intensive), we simply always allow the list view to be
        viewed, and limit further functionality when relevant.
        """
        ...

    def user_can_create(self, user): # -> bool:
        """
        For models extending Page, whether or not a page of this type can be
        added somewhere in the tree essentially determines the add permission,
        rather than actual model-wide permissions
        """
        ...

    def user_can_edit_obj(self, user, obj):
        ...

    def user_can_delete_obj(self, user, obj):
        ...

    def user_can_unpublish_obj(self, user, obj):
        ...

    def user_can_copy_obj(self, user, obj):
        ...
