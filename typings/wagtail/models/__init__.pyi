# ruff: noqa[ANN401]
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
from typing import Any, ClassVar, Generic, Self, type_check_only
from typing_extensions import TypeVar

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.checks import CheckMessage
from django.db import models
from django.db.models import Manager, ManyToManyField, Model, Q, QuerySet
from django.db.models.base import ModelBase
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from django.forms import Form
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.template.response import TemplateResponse
from django.utils.functional import cached_property as cached_property
from django_stubs_ext import StrOrPromise
from modelcluster.models import ClusterableModel
from wagtail.actions.copy_for_translation import CopyPageForTranslationAction as CopyPageForTranslationAction
from wagtail.actions.copy_page import CopyPageAction as CopyPageAction
from wagtail.actions.create_alias import CreatePageAliasAction as CreatePageAliasAction
from wagtail.actions.delete_page import DeletePageAction as DeletePageAction
from wagtail.actions.move_page import MovePageAction as MovePageAction
from wagtail.actions.publish_page_revision import PublishPageRevisionAction as PublishPageRevisionAction
from wagtail.actions.publish_revision import PublishRevisionAction as PublishRevisionAction
from wagtail.actions.unpublish import UnpublishAction as UnpublishAction
from wagtail.actions.unpublish_page import UnpublishPageAction as UnpublishPageAction
from wagtail.admin.panels.base import Panel
from wagtail.coreutils import (
    WAGTAIL_APPEND_SLASH as WAGTAIL_APPEND_SLASH,
    camelcase_to_underscore as camelcase_to_underscore,
    get_content_type_label as get_content_type_label,
    get_supported_content_language_variant as get_supported_content_language_variant,
    resolve_model_string as resolve_model_string,
    safe_md5 as safe_md5,
)
from wagtail.fields import StreamField as StreamField
from wagtail.forms import TaskStateCommentForm as TaskStateCommentForm
from wagtail.locks import (
    BaseLock,
    BasicLock as BasicLock,
    ScheduledForPublishLock as ScheduledForPublishLock,
    WorkflowLock as WorkflowLock,
)
from wagtail.log_actions import log as log
from wagtail.permissions import PagePermissionPolicy
from wagtail.query import PageQuerySet as PageQuerySet, SpecificQuerySetMixin as SpecificQuerySetMixin
from wagtail.search import index as index
from wagtail.signals import (
    page_published as page_published,
    page_slug_changed as page_slug_changed,
    pre_validate_delete as pre_validate_delete,
    task_approved as task_approved,
    task_cancelled as task_cancelled,
    task_rejected as task_rejected,
    task_submitted as task_submitted,
    workflow_approved as workflow_approved,
    workflow_cancelled as workflow_cancelled,
    workflow_rejected as workflow_rejected,
    workflow_submitted as workflow_submitted,
)
from wagtail.url_routing import RouteResult as RouteResult
from wagtail.utils.deprecation import RemovedInWagtail70Warning as RemovedInWagtail70Warning
from wagtail.utils.timestamps import ensure_utc as ensure_utc

from _typeshed import Incomplete
from treebeard.mp_tree import MP_Node, MP_NodeManager

from kausal_common.models.types import copy_signature

from .audit_log import (
    BaseLogEntry as BaseLogEntry,
    BaseLogEntryManager as BaseLogEntryManager,
    LogEntryQuerySet as LogEntryQuerySet,
    ModelLogEntry as ModelLogEntry,
)
from .i18n import (
    BootstrapTranslatableMixin as BootstrapTranslatableMixin,
    BootstrapTranslatableModel as BootstrapTranslatableModel,
    Locale as Locale,
    LocaleManager as LocaleManager,
    TranslatableMixin as TranslatableMixin,
    bootstrap_translatable_model as bootstrap_translatable_model,
    get_translatable_models as get_translatable_models,
)
from .media import (
    BaseCollectionManager as BaseCollectionManager,
    Collection as Collection,
    CollectionManager as CollectionManager,
    CollectionMember as CollectionMember,
    CollectionViewRestriction as CollectionViewRestriction,
    GroupCollectionPermission as GroupCollectionPermission,
    GroupCollectionPermissionManager as GroupCollectionPermissionManager,
    UploadedFile as UploadedFile,
    get_root_collection_id as get_root_collection_id,
)
from .reference_index import ReferenceIndex as ReferenceIndex
from .sites import Site as Site, SiteManager as SiteManager, SiteRootPath as SiteRootPath
from .specific import SpecificMixin as SpecificMixin
from .view_restrictions import BaseViewRestriction as BaseViewRestriction

PAGE_TEMPLATE_VAR: str
COMMENTS_RELATION_NAME: str

_F = TypeVar('_F', bound=Callable[..., Any])
@type_check_only
class _copy_signature(Generic[_F]):  # noqa: N801
    def __init__(self, target: _F) -> None: ...
    def __call__(self, wrapped: Callable[..., Any]) -> _F: ...


def reassign_root_page_locale_on_delete(sender, instance, **kwargs) -> None: ...

def get_page_models() -> Sequence[type[Page]]:
    """
    Returns a list of all non-abstract Page model classes defined in this project.
    """
def get_page_content_types(include_base_page_type: bool = True) -> QuerySet[ContentType]:
    """
    Returns a queryset of all ContentType objects corresponding to Page model classes.
    """
def get_default_page_content_type() -> ContentType:
    """
    Returns the content type to use as a default for pages whose content type
    has been deleted.
    """
def get_streamfield_names(model_class: type[Model]) -> tuple[str, ...]: ...


class PageBase(models.base.ModelBase):
    """Metaclass for Page"""
    def __init__(cls, name, bases, dct) -> None: ...  # noqa: N805


type SerializableData = dict[str, Any]


class RevisionMixin(models.Model):
    """A mixin that allows a model to have revisions."""
    latest_revision: models.ForeignKey[Revision[Self] | None]
    default_exclude_fields_in_copy: ClassVar[Iterable[str]]

    @property
    def revisions(self) -> QuerySet[Revision[Self]]:
        """
        Returns revisions that belong to the object.

        Subclasses should define a
        :class:`~django.contrib.contenttypes.fields.GenericRelation` to
        :class:`~wagtail.models.Revision` and override this property to return
        that ``GenericRelation``. This allows subclasses to customise the
        ``related_query_name`` of the ``GenericRelation`` and add custom logic
        (e.g. to always use the specific instance in ``Page``).
        """
    def get_base_content_type(self) -> ContentType: ...
    def get_content_type(self) -> ContentType: ...
    def get_latest_revision(self) -> Revision[Self] | None: ...
    def get_latest_revision_as_object(self) -> Self:
        """
        Returns the latest revision of the object as an instance of the model.
        If no latest revision exists, returns the object itself.
        """
    def serializable_data(self) -> SerializableData: ...
    @classmethod
    def from_serializable_data(cls, data: SerializableData, check_fks: bool = True, strict_fks: bool = False) -> Self: ...
    def with_content_json(self, content: SerializableData):
        """
        Returns a new version of the object with field values updated to reflect changes
        in the provided ``content`` (which usually comes from a previously-saved revision).

        Certain field values are preserved in order to prevent errors if the returned
        object is saved, such as ``id``. The following field values are also preserved,
        as they are considered to be meaningful to the object as a whole, rather than
        to a specific revision:

        * ``latest_revision``

        If :class:`~wagtail.models.TranslatableMixin` is applied, the following field values
        are also preserved:

        * ``translation_key``
        * ``locale``
        """
    def save_revision(  # noqa: PLR0913
        self, user: AbstractBaseUser | None = None, approved_go_live_at: str | datetime | None = None,
        changed: bool = True, log_action: bool = False, previous_revision: Revision[Any] | None = None,
        clean: bool = True,
    ) -> Revision[Any]:
        '''
        Creates and saves a revision.

        :param user: The user performing the action.
        :param approved_go_live_at: The date and time the revision is approved to go live.
        :param changed: Indicates whether there were any content changes.
        :param log_action: Flag for logging the action. Pass ``True`` to also create a log entry. Can be passed an action string.
            Defaults to ``"wagtail.edit"`` when no ``previous_revision`` param is passed, otherwise ``"wagtail.revert"``.
        :param previous_revision: Indicates a revision reversal. Should be set to the previous revision instance.
        :type previous_revision: Revision
        :param clean: Set this to ``False`` to skip cleaning object content before saving this revision.
        :return: The newly created revision.
        '''


type _DTSet = datetime | str
type _NullableDTF = models.DateTimeField[_DTSet | None, datetime | None]

class DraftStateMixin(models.Model):
    live: models.BooleanField
    has_unpublished_changes: models.BooleanField
    first_published_at: _NullableDTF
    last_published_at: _NullableDTF
    live_revision: models.ForeignKey[Revision[Self] | None]
    go_live_at: _NullableDTF
    expire_at: _NullableDTF
    expired: models.BooleanField

    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]: ...
    @property
    def approved_schedule(self) -> bool: ...
    @property
    def status_string(self) -> StrOrPromise: ...
    def publish(  # noqa: PLR0913
        self, revision: Revision[Any], user: AbstractBaseUser | None = None, changed: bool = True, log_action: bool = True,
        previous_revision: Revision[Any] | None = None, skip_permission_checks: bool = False,
    ) -> None:
        """
        Publish a revision of the object by applying the changes in the revision to the live object.

        :param revision: Revision to publish.
        :type revision: Revision
        :param user: The publishing user.
        :param changed: Indicated whether content has changed.
        :param log_action: Flag for the logging action, pass ``False`` to skip logging.
        :param previous_revision: Indicates a revision reversal. Should be set to the previous revision instance.
        :type previous_revision: Revision
        """
    def unpublish(
        self, set_expired: bool = False, commit: bool = True, user: AbstractBaseUser | None = None,
        log_action: bool = True,
    ):
        """
        Unpublish the live object.

        :param set_expired: Mark the object as expired.
        :param commit: Commit the changes to the database.
        :param user: The unpublishing user.
        :param log_action: Flag for the logging action, pass ``False`` to skip logging.
        """
    def with_content_json(self, content: SerializableData) -> Any:
        """
        Similar to :meth:`RevisionMixin.with_content_json`,
        but with the following fields also preserved:

        * ``live``
        * ``has_unpublished_changes``
        * ``first_published_at``
        """
    def get_latest_revision_as_object(self) -> Any: ...
    @cached_property
    def scheduled_revision(self) -> Revision | None: ...
    def get_scheduled_revision_as_object(self) -> Self: ...
    def get_lock(self) -> BaseLock | None: ...


class PreviewableMixin:
    """A mixin that allows a model to have previews."""
    def make_preview_request(
        self, original_request: HttpRequest | None = None, preview_mode: str | None = None,
        extra_request_attrs: dict[str, Any] | None = None,
    ) -> HttpResponseBase:
        """
        Simulate a request to this object, by constructing a fake HttpRequest object that is (as far
        as possible) representative of a real request to this object's front-end URL, and invoking
        serve_preview with that request (and the given preview_mode).

        Used for previewing / moderation and any other place where we
        want to display a view of this object in the admin interface without going through the regular
        page routing logic.

        If you pass in a real request object as original_request, additional information (e.g. client IP, cookies)
        will be included in the dummy request.
        """

    DEFAULT_PREVIEW_MODES: list[tuple[str, StrOrPromise]]

    @property
    def preview_modes(self) -> Sequence[tuple[str, StrOrPromise]]:
        """
        A list of ``(internal_name, display_name)`` tuples for the modes in which
        this object can be displayed for preview/moderation purposes. Ordinarily an object
        will only have one display mode, but subclasses can override this -
        for example, a page containing a form might have a default view of the form,
        and a post-submission 'thank you' page.
        Set to ``[]`` to completely disable previewing for this model.
        """
    @property
    def default_preview_mode(self) -> str:
        """
        The default preview mode to use in live preview.
        This default is also used in areas that do not give the user the option of selecting a
        mode explicitly, e.g. in the moderator approval workflow.
        If ``preview_modes`` is empty, an ``IndexError`` will be raised.
        """

    def is_previewable(self) -> bool:
        """Returns ``True`` if at least one preview mode is specified in ``preview_modes``."""

    def serve_preview(self, request: HttpRequest, mode_name: str):
        """
        Returns an HTTP response for use in object previews.

        This method can be overridden to implement custom rendering and/or
        routing logic.

        Any templates rendered during this process should use the ``request``
        object passed here - this ensures that ``request.user`` and other
        properties are set appropriately for the wagtail user bar to be
        displayed/hidden. This request will always be a GET.
        """
    def get_preview_context(self, request, mode_name: str) -> dict[str, Any]:
        """
        Returns a context dictionary for use in templates for previewing this object.
        """
    def get_preview_template(self, request, mode_name: str) -> str:
        """
        Returns a template to be used when previewing this object.

        Subclasses of ``PreviewableMixin`` must override this method to return the
        template name to be used in the preview. Alternatively, subclasses can also
        override the ``serve_preview`` method to completely customise the preview
        rendering logic.
        """

_UserT = TypeVar('_UserT', bound=AbstractBaseUser, default=AbstractBaseUser)

class LockableMixin(Generic[_UserT], models.Model):
    locked: models.BooleanField
    locked_at: _NullableDTF
    locked_by: models.ForeignKey[_UserT | None]

    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]: ...
    def with_content_json(self, content: SerializableData) -> Self:
        """
        Similar to :meth:`RevisionMixin.with_content_json`,
        but with the following fields also preserved:

        * ``locked``
        * ``locked_at``
        * ``locked_by``
        """
    def get_lock(self) -> BaseLock | None:
        """
        Returns a sub-class of ``BaseLock`` if the instance is locked, otherwise ``None``.
        """

class WorkflowMixin:
    """A mixin that allows a model to have workflows."""
    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]: ...
    @classmethod
    def get_default_workflow(cls) -> Workflow | None:
        """
        Returns the active workflow assigned to the model.

        For non-``Page`` models, workflows are assigned to the model's content type,
        thus shared across all instances instead of being assigned to individual
        instances (unless :meth:`~WorkflowMixin.get_workflow` is overridden).

        This method is used to determine the workflow to use when creating new
        instances of the model. On ``Page`` models, this method is unused as the
        workflow can be determined from the parent page's workflow.
        """
    @property
    def has_workflow(self) -> bool:
        """Returns True if the object has an active workflow assigned, otherwise False."""
    def get_workflow(self) -> Workflow | None:
        """Returns the active workflow assigned to the object."""
    @property
    def workflow_states(self) -> WorkflowStateQuerySet:
        """
        Returns workflow states that belong to the object.

        To allow filtering ``WorkflowState`` queries by the object,
        subclasses should define a
        :class:`~django.contrib.contenttypes.fields.GenericRelation` to
        :class:`~wagtail.models.WorkflowState` with the desired
        ``related_query_name``. This property can be replaced with the
        ``GenericRelation`` or overridden to allow custom logic, which can be
        useful if the model has inheritance.
        """
    @property
    def workflow_in_progress(self) -> bool:
        """Returns True if a workflow is in progress on the current object, otherwise False."""
    @property
    def current_workflow_state(self) -> WorkflowState | None:
        """Returns the in progress or needs changes workflow state on this object, if it exists."""
    @property
    def current_workflow_task_state(self):
        """Returns (specific class of) the current task state of the workflow on this object, if it exists."""
    @property
    def current_workflow_task(self):
        """Returns (specific class of) the current task in progress on this object, if it exists."""
    @property
    def status_string(self): ...
    def get_lock(self): ...


_PageModel = TypeVar('_PageModel', bound=Page, default='Page', covariant=True)

class BasePageManager(Generic[_PageModel], models.Manager[_PageModel]):
    def get_queryset(self) -> PageQuerySet[_PageModel]: ...
    def first_common_ancestor_of(self, pages: Sequence[Page], include_self: bool = False, strict: bool = False) -> Page:
        """
        This is similar to `PageQuerySet.first_common_ancestor` but works
        for a list of pages instead of a queryset.
        """

class PageManager(BasePageManager[_PageModel], MP_NodeManager): ...




class AbstractPage(models.Model):
    """
    Abstract superclass for Page. According to Django's inheritance rules, managers set on
    abstract models are inherited by subclasses, but managers set on concrete models that are extended
    via multi-table inheritance are not. We therefore need to attach PageManager to an abstract
    superclass to ensure that it is retained by subclasses of Page.
    """

    objects: ClassVar[PageManager[Any]]  # pyright: ignore

PAGE_PERMISSION_TYPES: list[tuple[str, StrOrPromise, StrOrPromise]]
PAGE_PERMISSION_TYPE_CHOICES: list[tuple[str, StrOrPromise]]
PAGE_PERMISSION_CODENAMES: list[str]


class Page(  # pyright: ignore[reportGeneralTypeIssues]
    AbstractPage,
    WorkflowMixin,
    PreviewableMixin,
    DraftStateMixin,
    LockableMixin,
    RevisionMixin,
    TranslatableMixin[PageQuerySet],
    MP_Node[PageQuerySet[Page]],
    SpecificMixin[Page], index.Indexed, ClusterableModel, metaclass=PageBase,
):
    title: models.CharField
    draft_title: models.CharField
    slug: models.SlugField
    content_type: models.ForeignKey[ContentType]
    url_path: models.TextField
    owner: models.ForeignKey[AbstractBaseUser | None]
    seo_title: models.CharField
    show_in_menus_default: bool
    show_in_menus: models.BooleanField
    search_description: models.TextField
    latest_revision_created_at: _NullableDTF
    alias_of: models.ForeignKey[Self | None, Self | None]
    search_fields: Sequence[index.BaseField]
    is_creatable: bool
    max_count: int | None
    max_count_per_parent: int | None
    admin_default_ordering: str
    exclude_fields_in_copy: list[str]
    default_exclude_fields_in_copy: ClassVar[Iterable[str]]
    content_panels: Sequence[Panel]
    promote_panels: Sequence[Panel]
    settings_panels: Sequence[Panel]
    private_page_options: Sequence[str]

    _default_manager: ClassVar[PageManager[Self]]
    objects: ClassVar[PageManager[Self]]  # pyright: ignore

    aliases: ReverseManyToOneDescriptor[Self]
    sites_rooted_here: ReverseManyToOneDescriptor[Site]

    @staticmethod
    def route_for_request(request: HttpRequest, path: str) -> RouteResult | None:
        """
        Find the page route for the given HTTP request object, and URL path. The route
        result (`page`, `args`, and `kwargs`) will be cached via
        `request._wagtail_route_for_request`.
        """
    @staticmethod
    def find_for_request(request: HttpRequest, path: str) -> Page | None:
        """
        Find the page for the given HTTP request object, and URL path. The full
        page route will be cached via `request._wagtail_route_for_request`
        """

    # def __init__(self, *args, **kwargs) -> None: ...

    @property
    def revisions(self) -> QuerySet[Revision[Self]]: ...
    def get_base_content_type(self) -> ContentType: ...
    def get_content_type(self) -> ContentType: ...
    @classmethod
    def get_streamfield_names(cls) -> tuple[str, ...]: ...
    def set_url_path(self, parent: Page | None) -> str:
        """
        Populate the url_path field based on this page's slug and the specified parent page.
        (We pass a parent in here, rather than retrieving it via get_parent, so that we can give
        new unsaved pages a meaningful URL when previewing them; at that point the page has not
        been assigned a position in the tree, as far as treebeard is concerned.
        """
    def get_default_locale(self) -> Locale:
        """
        Finds the default locale to use for this page.

        This will be called just before the initial save.
        """
    def get_admin_default_ordering(self) -> str:
        """
        Determine the default ordering for child pages in the admin index listing.
        Returns a string (e.g. 'latest_revision_created_at, title, ord' or 'live').
        """

    def full_clean(self, *args, **kwargs) -> None: ...
    def clean(self) -> None: ...
    def is_site_root(self) -> bool:
        """
        Returns True if this page is the root of any site.

        This includes translations of site root pages as well.
        """
    def save(  # noqa: DJ012, PLR0913
        self, force_insert: bool | tuple[ModelBase, ...] = ..., force_update: bool = ...,
        using: str | None = ..., update_fields: Iterable[str] | None = ...,
        clean: bool = True, user: AbstractBaseUser | None = None, log_action: bool = False,
    ):
        """
        Overrides default method behaviour to make additional updates unique to pages,
        such as updating the ``url_path`` value of descendant page to reflect changes
        to this page's slug.

        New pages should generally be saved via the `add_child() <https://django-treebeard.readthedocs.io/en/latest/mp_tree.html#treebeard.mp_tree.MP_Node.add_child>`_ or `add_sibling() <https://django-treebeard.readthedocs.io/en/latest/mp_tree.html#treebeard.mp_tree.MP_Node.add_sibling>`_
        method of an existing page, which will correctly set the ``path`` and ``depth``
        fields on the new page before saving it.

        By default, pages are validated using ``full_clean()`` before attempting to
        save changes to the database, which helps to preserve validity when restoring
        pages from historic revisions (which might not necessarily reflect the current
        model state). This validation step can be bypassed by calling the method with
        ``clean=False``.
        """
    def delete(self, *args, **kwargs): ...
    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]: ...
    @property
    def page_type_display_name(self) -> StrOrPromise:
        """
        A human-readable version of this page's type
        """
    def route(self, request: HttpRequest, path_components: Sequence[str]) -> RouteResult: ...
    def get_admin_display_title(self) -> StrOrPromise:
        """
        Return the title for this page as it should appear in the admin backend;
        override this if you wish to display extra contextual information about the page,
        such as language. By default, returns ``draft_title``.
        """

    @_copy_signature(RevisionMixin.save_revision)
    def save_revision(self, *args, **kwargs) -> Revision[Self]: ...

    def get_latest_revision_as_object(self) -> Self: ...
    def update_aliases(
        self, *, revision: Revision | None = None, _content: SerializableData | None = None, _updated_ids: Sequence[int] | None = None
    ) -> None:
        """
        Publishes all aliases that follow this page with the latest content from this page.

        This is called by Wagtail whenever a page with aliases is published.

        :param revision: The revision of the original page that we are updating to (used for logging purposes)
        :type revision: Revision, Optional
        """
    @_copy_signature(DraftStateMixin.publish)
    def publish(self, *args, **kwargs) -> None: ...

    @_copy_signature(DraftStateMixin.unpublish)
    def unpublish(self, set_expired: bool = False, commit: bool = True, user: Incomplete | None = None, log_action: bool = True): ...
    context_object_name: str | None = None
    def get_context(self, request: HttpRequest, *args, **kwargs) -> dict[str, Any]: ...
    def get_preview_context(self, request, mode_name: str) -> dict[str, Any]: ...
    def get_template(self, request, *args, **kwargs) -> str: ...
    def get_preview_template(self, request, mode_name) -> str: ...
    def serve(self, request, *args, **kwargs) -> TemplateResponse: ...
    def is_navigable(self) -> bool:
        """
        Return true if it's meaningful to browse subpages of this page -
        i.e. it currently has subpages,
        or it's at the top level (this rule necessary for empty out-of-the-box sites to have working navigation)
        """
    def get_url_parts(self, request: HttpRequest | None = None) -> tuple[int, str, str] | None:
        """
        Determine the URL for this page and return it as a tuple of
        ``(site_id, site_root_url, page_url_relative_to_site_root)``.
        Return None if the page is not routable.

        This is used internally by the ``full_url``, ``url``, ``relative_url``
        and ``get_site`` properties and methods; pages with custom URL routing
        should override this method in order to have those operations return
        the custom URLs.

        Accepts an optional keyword argument ``request``, which may be used
        to avoid repeated database / cache lookups. Typically, a page model
        that overrides ``get_url_parts`` should not need to deal with
        ``request`` directly, and should just pass it to the original method
        when calling ``super``.
        """
    def get_full_url(self, request: HttpRequest | None = None) -> str | None:
        """Return the full URL (including protocol / domain) to this page, or None if it is not routable"""
    @property
    def full_url(self) -> str | None: ...
    def get_url(self, request: HttpRequest | None = None, current_site: Site | None = None):
        """
        Return the 'most appropriate' URL for referring to this page from the pages we serve,
        within the Wagtail backend and actual website templates;
        this is the local URL (starting with '/') if we're only running a single site
        (i.e. we know that whatever the current page is being served from, this link will be on the
        same domain), and the full URL (with domain) if not.
        Return None if the page is not routable.

        Accepts an optional but recommended ``request`` keyword argument that, if provided, will
        be used to cache site-level URL information (thereby avoiding repeated database / cache
        lookups) and, via the ``Site.find_for_request()`` function, determine whether a relative
        or full URL is most appropriate.
        """

    @property
    def url(self) -> str | None: ...

    def relative_url(self, current_site, request: Incomplete | None = None):
        """
        Return the 'most appropriate' URL for this page taking into account the site we're currently on;
        a local URL if the site matches, or a fully qualified one otherwise.
        Return None if the page is not routable.

        Accepts an optional but recommended ``request`` keyword argument that, if provided, will
        be used to cache site-level URL information (thereby avoiding repeated database / cache
        lookups).
        """
    def get_site(self) -> Site | None:
        """
        Return the Site object that this page belongs to.
        """
    @classmethod
    def get_indexed_objects(cls) -> QuerySet[Page]: ...
    def get_indexed_instance(self) -> Page: ...
    @classmethod
    def clean_subpage_models(cls) -> Sequence[type[Page]]:
        """
        Returns the list of subpage types, normalised as model classes.
        Throws ValueError if any entry in subpage_types cannot be recognised as a model name,
        or LookupError if a model does not exist (or is not a Page subclass).
        """
    @classmethod
    def clean_parent_page_models(cls) -> Sequence[type[Page]]:
        """
        Returns the list of parent page types, normalised as model classes.
        Throws ValueError if any entry in parent_page_types cannot be recognised as a model name,
        or LookupError if a model does not exist (or is not a Page subclass).
        """
    @classmethod
    def allowed_parent_page_models(cls) -> Sequence[type[Page]]:
        """
        Returns the list of page types that this page type can be a subpage of,
        as a list of model classes
        """
    @classmethod
    def allowed_subpage_models(cls) -> Sequence[type[Page]]:
        """
        Returns the list of page types that this page type can have as subpages,
        as a list of model classes
        """
    @classmethod
    def creatable_subpage_models(cls) -> Sequence[type[Page]]:
        """
        Returns the list of page types that may be created under this page type,
        as a list of model classes
        """
    @classmethod
    def can_exist_under(cls, parent: Page) -> bool:
        """
        Checks if this page type can exist as a subpage under a parent page
        instance.

        See also: :func:`Page.can_create_at` and :func:`Page.can_move_to`
        """
    @classmethod
    def can_create_at(cls, parent: Page) -> bool:
        """
        Checks if this page type can be created as a subpage under a parent
        page instance.
        """
    def can_move_to(self, parent: Page) -> bool:
        """
        Checks if this page instance can be moved to be a subpage of a parent
        page instance.
        """
    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        '''
        Returns the human-readable "verbose name" of this page model e.g "Blog page".
        '''
    @classmethod
    def get_page_description(cls) -> str:
        '''
        Returns a page description if it\'s set. For example "A multi-purpose web page".
        '''
    @property
    def approved_schedule(self): ...
    def has_unpublished_subtree(self):
        """
        An awkwardly-defined flag used in determining whether unprivileged editors have
        permission to delete this article. Returns true if and only if this page is non-live,
        and it has no live children.
        """
    def move(self, target, pos: Incomplete | None = None, user: Incomplete | None = None):
        """
        Extension to the treebeard 'move' method to ensure that url_path is updated,
        and to emit a 'pre_page_move' and 'post_page_move' signals.
        """
    def copy(
        self,
        recursive: bool = False,
        to: Page | None = None,
        update_attrs: dict[str, Any] | None = None,
        copy_revisions: bool = True,
        keep_live: bool = True,
        user: AbstractBaseUser | None = None,
        process_child_object: Callable | None = None,
        exclude_fields: Sequence[str] | None = None,
        log_action: str = 'wagtail.copy',
        reset_translation_key: bool = True,
    ) -> Self:
        """
        Copies a given page

        :param log_action: flag for logging the action. Pass None to skip logging. Can be passed an action string. Defaults to 'wagtail.copy'
        """
    def create_alias(  # noqa: PLR0913
        self,
        *,
        recursive: bool = False,
        parent: Page | None = None,
        update_slug: str | None = None,
        update_locale: Locale | None = None,
        user: AbstractBaseUser | None = None,
        log_action: str = 'wagtail.create_alias',
        reset_translation_key: bool = True,
        _mpnode_attrs: tuple[str, int] | None = None,
    ) -> Self: ...
    def copy_for_translation(
        self, locale: Locale, *, copy_parents: bool = False, alias: bool = False, exclude_fields: Sequence[str] | None = None,
    ) -> Self:
        """Creates a copy of this page in the specified locale."""
    def permissions_for_user(self, user: AbstractBaseUser) -> PagePermissionTester:
        """
        Return a PagePermissionsTester object defining what actions the user can perform on this page
        """
    def is_previewable(self) -> bool:
        """Returns True if at least one preview mode is specified"""
    def get_route_paths(self) -> list[str]:
        """
        Returns a list of paths that this page can be viewed at.

        These values are combined with the dynamic portion of the page URL to
        automatically create redirects when the page's URL changes.

        .. note::

            If using ``RoutablePageMixin``, you may want to override this method
            to include the paths of popualar routes.

        .. note::

            Redirect paths are 'normalized' to apply consistent ordering to GET parameters,
            so you don't need to include every variation. Fragment identifiers are discarded
            too, so should be avoided.
        """
    def get_cached_paths(self):
        """
        This returns a list of paths to invalidate in a frontend cache
        """
    def get_cache_key_components(self):
        """
        The components of a :class:`Page` which make up the :attr:`cache_key`. Any change to a
        page should be reflected in a change to at least one of these components.
        """
    @property
    def cache_key(self):
        """
        A generic cache key to identify a page in its current state.
        Should the page change, so will the key.

        Customizations to the cache key should be made in :attr:`get_cache_key_components`.
        """
    def get_sitemap_urls(self, request: Incomplete | None = None): ...
    def get_ancestors(self, inclusive: bool = False) -> PageQuerySet:
        """
        Returns a queryset of the current page's ancestors, starting at the root page
        and descending to the parent, or to the current page itself if ``inclusive`` is true.
        """
    def get_descendants(self, inclusive: bool = False) -> PageQuerySet:
        """
        Returns a queryset of all pages underneath the current page, any number of levels deep.
        If ``inclusive`` is true, the current page itself is included in the queryset.
        """
    def get_siblings(self, inclusive: bool = True) -> PageQuerySet:
        """
        Returns a queryset of all other pages with the same parent as the current page.
        If ``inclusive`` is true, the current page itself is included in the queryset.
        """
    def get_next_siblings(self, inclusive: bool = False) -> PageQuerySet: ...
    def get_prev_siblings(self, inclusive: bool = False) -> PageQuerySet: ...
    def get_view_restrictions(self) -> PageViewRestriction:
        """
        Return a query set of all page view restrictions that apply to this page.

        This checks the current page and all ancestor pages for page view restrictions.

        If any of those pages are aliases, it will resolve them to their source pages
        before querying PageViewRestrictions so alias pages use the same view restrictions
        as their source page and they cannot have their own.
        """
    password_required_template: Incomplete
    def serve_password_required_response(self, request, form, action_url):
        """
        Serve a response indicating that the user has been denied access to view this page,
        and must supply a password.
        form = a Django form object containing the password input
            (and zero or more hidden fields that also need to be output on the template)
        action_url = URL that this form should be POSTed to
        """
    def with_content_json(self, content: SerializableData) -> Self:
        """
        Returns a new version of the page with field values updated to reflect changes
        in the provided ``content`` (which usually comes from a previously-saved
        page revision).

        Certain field values are preserved in order to prevent errors if the returned
        page is saved, such as ``id``, ``content_type`` and some tree-related values.
        The following field values are also preserved, as they are considered to be
        meaningful to the page as a whole, rather than to a specific revision:

        * ``draft_title``
        * ``live``
        * ``has_unpublished_changes``
        * ``owner``
        * ``locked``
        * ``locked_by``
        * ``locked_at``
        * ``latest_revision``
        * ``latest_revision_created_at``
        * ``first_published_at``
        * ``alias_of``
        * ``wagtail_admin_comments`` (COMMENTS_RELATION_NAME)
        """
    @property
    def has_workflow(self) -> bool:
        """Returns True if the page or an ancestor has an active workflow assigned, otherwise False"""
    #def get_workflow(self) -> Workflow | None:
    #    """Returns the active workflow assigned to the page or its nearest ancestor"""


class Orderable(models.Model):
    sort_order: models.IntegerField[int | None, int | None]
    sort_order_field: str

    class Meta:
        abstract: bool = ...
        ordering: list[str]


_RevTargetT = TypeVar('_RevTargetT', bound=Model, default=Model)


class RevisionQuerySet(Generic[_RevTargetT], models.QuerySet[Revision[_RevTargetT]]):
    def page_revisions_q(self) -> Q: ...
    def page_revisions(self) -> RevisionQuerySet[Page]: ...
    def not_page_revisions(self) -> Self: ...
    def for_instance[M: Model](self, instance: M) -> RevisionQuerySet[M]: ...


class RevisionsManager(Generic[_RevTargetT], models.Manager[Revision[_RevTargetT]]):
    def get_queryset(self) -> RevisionQuerySet[_RevTargetT]: ...
    def previous_revision_id_subquery(self, revision_fk_name: str = 'revision'):
        """
        Returns a Subquery that can be used to annotate a queryset with the ID
        of the previous revision, based on the revision_fk_name field. Useful
        to avoid N+1 queries when generating comparison links between revisions.

        The logic is similar to Revision.get_previous().pk.
        """

class PageRevisionsManager(RevisionsManager[Page]):
    def get_queryset(self) -> RevisionQuerySet[Page]: ...


class Revision[M: Model](models.Model):
    content_type: models.ForeignKey[ContentType]
    base_content_type: models.ForeignKey[ContentType]
    object_id: models.CharField
    created_at: models.DateTimeField[_DTSet, datetime]
    user: models.ForeignKey[AbstractBaseUser | None]
    object_str: models.TextField
    content: models.JSONField
    approved_go_live_at: _NullableDTF
    objects: ClassVar[RevisionsManager]  # pyright: ignore
    _default_manager: ClassVar[RevisionsManager]
    page_revisions: ClassVar[PageRevisionsManager]
    content_object: GenericForeignKey
    wagtail_reference_index_ignore: bool
    @cached_property
    def base_content_object(self) -> Model: ...
    base_content_type_id: int
    def save(self, user: AbstractBaseUser | None = None, *args, **kwargs) -> None: ...  # type: ignore  # noqa: DJ012
    def as_object(self) -> M: ...
    def is_latest_revision(self) -> bool: ...
    def delete(self) -> tuple[int, dict[str, int]]: ...  # type: ignore
    def publish(
        self, user: AbstractBaseUser | None = None, changed: bool = True,
        log_action: bool = True, previous_revision: Revision[M] | None = None,
        skip_permission_checks: bool = False,
    ): ...
    def get_previous(self) -> Self: ...
    def get_next(self) -> Self: ...


class GroupPagePermissionManager(models.Manager):
    def create(self, **kwargs): ...


class GroupPagePermission(models.Model):
    group: models.ForeignKey[Group]
    page: models.ForeignKey[Page]
    permission: models.ForeignKey[Permission]
    objects: ClassVar[GroupPagePermissionManager]  # pyright: ignore


class PagePermissionTester:
    user: AbstractBaseUser
    permission_policy: PagePermissionPolicy
    page: Page
    page_is_root: bool
    permissions: set[str]
    def __init__(self, user: AbstractBaseUser, page: Page) -> None: ...
    def user_has_lock(self) -> bool: ...
    def page_locked(self) -> bool: ...
    def can_add_subpage(self) -> bool: ...
    def can_edit(self) -> bool: ...
    def can_delete(self, ignore_bulk: bool = False) -> bool: ...
    def can_unpublish(self) -> bool: ...
    def can_publish(self) -> bool: ...
    def can_submit_for_moderation(self) -> bool: ...
    def can_set_view_restrictions(self) -> bool: ...
    def can_unschedule(self) -> bool: ...
    def can_lock(self) -> bool: ...
    def can_unlock(self) -> bool: ...
    def can_publish_subpage(self) -> bool:
        """
        Niggly special case for creating and publishing a page in one go.
        Differs from can_publish in that we want to be able to publish subpages of root, but not
        to be able to publish root itself. (Also, can_publish_subpage returns false if the page
        does not allow subpages at all.)
        """
    def can_reorder_children(self) -> bool:
        """
        Keep reorder permissions the same as publishing, since it immediately affects published pages
        (and the use-cases for a non-admin needing to do it are fairly obscure...)
        """
    def can_move(self) -> bool:
        """
        Moving a page should be logically equivalent to deleting and re-adding it (and all its children).
        As such, the permission test for 'can this be moved at all?' should be the same as for deletion.
        (Further constraints will then apply on where it can be moved *to*.)
        """
    def can_copy(self) -> bool: ...
    def can_move_to(self, destination: Page): ...
    def can_copy_to(self, destination: Page, recursive: bool = False) -> bool: ...
    def can_view_revisions(self) -> bool: ...


class PageViewRestriction(BaseViewRestriction):
    page: models.ForeignKey[Page, Page]
    passed_view_restrictions_session_key: str

    def save(self, user: AbstractBaseUser | None = None, **kwargs) -> None:  # type: ignore
        """
        Custom save handler to include logging.
        :param user: the user add/updating the view restriction
        :param specific_instance: the specific model instance the restriction applies to
        """
    def delete(self, user: AbstractBaseUser | None = None, **kwargs):  # type: ignore
        """
        Custom delete handler to aid in logging
        :param user: the user removing the view restriction
        """


class WorkflowPage(models.Model):
    page: Page
    workflow: Workflow
    def get_pages(self) -> PageQuerySet:
        """
        Returns a queryset of pages that are affected by this WorkflowPage link.

        This includes all descendants of the page excluding any that have other WorkflowPages.
        """


class WorkflowContentType(models.Model):
    content_type: ContentType
    workflow: Workflow


class WorkflowTask(Orderable):
    workflow: Workflow
    task: WorkflowTask

    class Meta(Orderable.Meta): ...


class TaskQuerySet(SpecificQuerySetMixin, models.QuerySet):
    def active(self): ...

class TaskManager(models.Manager[Task]):
    def get_queryset(self) -> TaskQuerySet: ...


_StateT = TypeVar('_StateT', bound=TaskState, default='TaskState')


class Task(Generic[_StateT], SpecificMixin['Task'], models.Model):
    name: models.CharField
    content_type: models.ForeignKey[ContentType]
    active: models.BooleanField

    objects: ClassVar[TaskManager]  # type: ignore
    _default_manager: ClassVar[TaskManager]

    admin_form_fields: list[str]
    admin_form_readonly_on_edit_fields: list[str]

    def __init__(self, *args, **kwargs) -> None: ...
    @property
    def workflows(self) -> QuerySet[Workflow]:
        """Returns all ``Workflow`` instances that use this task"""
    @property
    def active_workflows(self) -> QuerySet[Workflow]:
        """Return a ``QuerySet``` of active workflows that this task is part of"""
    @classmethod
    def get_verbose_name(cls) -> StrOrPromise:
        '''
        Returns the human-readable "verbose name" of this task model e.g "Group approval task".
        '''

    task_state_class: type[_StateT] | None

    @classmethod
    def get_task_state_class(cls) -> type[_StateT]: ...

    def start(self, workflow_state: WorkflowState, user: AbstractBaseUser | None = None) -> _StateT:
        """Start this task on the provided workflow state by creating an instance of TaskState"""
    def on_action(self, task_state: _StateT, user: AbstractBaseUser, action_name: str, **kwargs) -> None:
        """Performs an action on a task state determined by the ``action_name`` string passed"""
    def user_can_access_editor(self, obj, user):
        """Returns True if a user who would not normally be able to access the editor for the object should be able to if the object is currently on this task.
        Note that returning False does not remove permissions from users who would otherwise have them."""
    def locked_for_user(self, obj, user):
        """
        Returns True if the object should be locked to a given user's edits.
        This can be used to prevent editing by non-reviewers.
        """
    def user_can_lock(self, obj, user):
        """Returns True if a user who would not normally be able to lock the object should be able to if the object is currently on this task.
        Note that returning False does not remove permissions from users who would otherwise have them."""
    def user_can_unlock(self, obj, user):
        """Returns True if a user who would not normally be able to unlock the object should be able to if the object is currently on this task.
        Note that returning False does not remove permissions from users who would otherwise have them."""
    def get_actions(self, obj, user) -> Sequence[tuple[str, StrOrPromise, bool]]:
        """
        Get the list of action strings (name, verbose_name, whether the action requires additional data - see
        ``get_form_for_action``) for actions the current user can perform for this task on the given object.
        These strings should be the same as those able to be passed to ``on_action``
        """
    def get_form_for_action(self, action) -> type[Form]: ...
    def get_template_for_action(self, action) -> str: ...
    def get_task_states_user_can_moderate(self, user, **kwargs) -> TaskStateQuerySet:
        """Returns a ``QuerySet`` of the task states the current user can moderate"""
    @classmethod
    def get_description(cls) -> str:
        """Returns the task description."""

    def deactivate(self, user: AbstractBaseUser | None = None) -> None:
        """Set ``active`` to False and cancel all in progress task states linked to this task"""

class WorkflowManager(models.Manager):
    def active(self): ...

class AbstractWorkflow(ClusterableModel):
    name: Incomplete
    active: Incomplete
    objects: Incomplete
    @property
    def tasks(self):
        """Returns all ``Task`` instances linked to this workflow"""
    def start(self, obj, user):
        """Initiates a workflow by creating an instance of ``WorkflowState``"""
    def deactivate(self, user: Incomplete | None = None) -> None:
        """Sets the workflow as inactive, and cancels all in progress instances of ``WorkflowState`` linked to this workflow"""
    def all_pages(self):
        """
        Returns a queryset of all the pages that this Workflow applies to.
        """
    class Meta:
        verbose_name: Incomplete
        verbose_name_plural: Incomplete
        abstract: bool

class Workflow(AbstractWorkflow): ...

class AbstractGroupApprovalTask(Task):
    groups: ManyToManyField[Group, Any]
    admin_form_fields: Incomplete
    admin_form_widgets: Incomplete

    class Meta:
        abstract: bool
        verbose_name: Incomplete
        verbose_name_plural: Incomplete

    def start(self, workflow_state, user: Incomplete | None = None): ...
    def user_can_access_editor(self, obj, user): ...
    def locked_for_user(self, obj, user): ...
    def user_can_lock(self, obj, user): ...
    def user_can_unlock(self, obj, user): ...
    def get_actions(self, obj, user): ...
    def get_task_states_user_can_moderate(self, user, **kwargs): ...
    @classmethod
    def get_description(cls) -> str: ...

class GroupApprovalTask(AbstractGroupApprovalTask): ...

class WorkflowStateQuerySet(models.QuerySet):
    def active(self):
        """
        Filters to only STATUS_IN_PROGRESS and STATUS_NEEDS_CHANGES WorkflowStates
        """
    def for_instance(self, instance):
        """
        Filters to only WorkflowStates for the given instance
        """

#_WorkflowStateManager = models.Manager['WorkflowState'].from_queryset(WorkflowStateQuerySet)
#class WorkflowStateManager(_WorkflowStateManager):
#    def get_queryset(self) -> WorkflowStateQuerySet: ...


class WorkflowState(models.Model):
    """Tracks the status of a started Workflow on an object."""
    STATUS_IN_PROGRESS: str
    STATUS_APPROVED: str
    STATUS_NEEDS_CHANGES: str
    STATUS_CANCELLED: str
    STATUS_CHOICES: Incomplete
    content_type: Incomplete
    base_content_type: Incomplete
    object_id: Incomplete
    content_object: Incomplete
    workflow: Incomplete
    status: Incomplete
    created_at: Incomplete
    requested_by: Incomplete
    current_task_state: Incomplete
    on_finish: Incomplete
    objects: ClassVar[Manager[WorkflowState]]  # pyright: ignore
    _default_manager: ClassVar[Manager[WorkflowState]]

    def clean(self) -> None: ...
    def save(self, *args, **kwargs): ...
    def resume(self, user: Incomplete | None = None):
        """Put a STATUS_NEEDS_CHANGES workflow state back into STATUS_IN_PROGRESS, and restart the current task"""
    def user_can_cancel(self, user): ...
    def update(self, user: Incomplete | None = None, next_task: Incomplete | None = None) -> None:
        """Checks the status of the current task, and progresses (or ends) the workflow if appropriate. If the workflow progresses,
        next_task will be used to start a specific task next if provided."""
    @property
    def successful_task_states(self): ...
    def get_next_task(self):
        """Returns the next active task, which has not been either approved or skipped"""
    def cancel(self, user: Incomplete | None = None) -> None:
        """Cancels the workflow state"""
    def finish(self, user: Incomplete | None = None) -> None:
        """Finishes a successful in progress workflow, marking it as approved and performing the ``on_finish`` action"""
    def copy_approved_task_states_to_revision(self, revision) -> None:
        """This creates copies of previously approved task states with revision set to a different revision."""
    def revisions(self):
        """Returns all revisions associated with task states linked to the current workflow state"""
    def all_tasks_with_status(self):
        """
        Returns a list of Task objects that are linked with this workflow state's
        workflow. The status of that task in this workflow state is annotated in the
        `.status` field. And a displayable version of that status is annotated in the
        `.status_display` field.

        This is different to querying TaskState as it also returns tasks that haven't
        been started yet (so won't have a TaskState).
        """
    def all_tasks_with_state(self):
        '''
        Returns a list of Task objects that are linked with this WorkflowState\'s
        workflow, and have the latest task state.

        In a "Submit for moderation -> reject at step 1 -> resubmit -> accept" workflow, this ensures
        the task list reflects the accept, rather than the reject.
        '''
    @property
    def is_active(self): ...
    @property
    def is_at_final_task(self):
        """Returns the next active task, which has not been either approved or skipped"""


class BaseTaskStateManager[M: Model](models.Manager[M]):
    def reviewable_by(self, user): ...


class TaskStateQuerySet(SpecificQuerySetMixin, models.QuerySet[TaskState]):
    def for_instance(self, instance: Model):
        """
        Filters to only TaskStates for the given instance
        """

class TaskStateManager(BaseTaskStateManager[TaskState]):
     def get_queryset(self) -> TaskStateQuerySet: ...


class TaskState(SpecificMixin['TaskState'], models.Model):
    """Tracks the status of a given Task for a particular revision."""
    STATUS_IN_PROGRESS: str
    STATUS_APPROVED: str
    STATUS_REJECTED: str
    STATUS_SKIPPED: str
    STATUS_CANCELLED: str
    STATUS_CHOICES: Incomplete
    workflow_state: Incomplete
    revision: Incomplete
    task: Incomplete
    status: Incomplete
    started_at: Incomplete
    finished_at: Incomplete
    finished_by: Incomplete
    comment: Incomplete
    content_type: Incomplete
    exclude_fields_in_copy: Incomplete
    default_exclude_fields_in_copy: Incomplete

    objects: ClassVar[TaskStateManager]  # pyright: ignore
    _default_manager: ClassVar[TaskStateManager]

    def __init__(self, *args, **kwargs) -> None: ...
    def approve(self, user: Incomplete | None = None, update: bool = True, comment: str = ''):
        """Approve the task state and update the workflow state"""
    def reject(self, user: Incomplete | None = None, update: bool = True, comment: str = ''):
        """Reject the task state and update the workflow state"""
    @cached_property
    def task_type_started_at(self):
        """Finds the first chronological started_at for successive TaskStates - ie started_at if the task had not been restarted"""
    def cancel(self, user: Incomplete | None = None, resume: bool = False, comment: str = ''):
        """Cancel the task state and update the workflow state. If ``resume`` is set to True, then upon update the workflow state
        is passed the current task as ``next_task``, causing it to start a new task state on the current task if possible"""
    def copy(self, update_attrs: Incomplete | None = None, exclude_fields: Incomplete | None = None):
        """Copy this task state, excluding the attributes in the ``exclude_fields`` list and updating any attributes to values
        specified in the ``update_attrs`` dictionary of ``attribute``: ``new value`` pairs"""
    def get_comment(self):
        """
        Returns a string that is displayed in workflow history.

        This could be a comment by the reviewer, or generated.
        Use mark_safe to return HTML.
        """
    def log_state_change_action(self, user, action) -> None:
        """Log the approval/rejection action"""


class PageLogEntryQuerySet(LogEntryQuerySet):
    def get_content_type_ids(self): ...
    def filter_on_content_type(self, content_type): ...

class PageLogEntryManager(BaseLogEntryManager):
    def get_queryset(self): ...
    def get_instance_title(self, instance): ...
    def log_action(self, instance, action, **kwargs): ...
    def viewable_by_user(self, user): ...
    def for_instance(self, instance): ...

class PageLogEntry(BaseLogEntry):
    page: Incomplete
    objects: Incomplete

    @cached_property
    def object_id(self) -> int: ...  # type: ignore[override]
    @cached_property
    def message(self): ...


class Comment(ClusterableModel):
    """
    A comment on a field, or a field within a streamfield block
    """
    page: Incomplete
    user: Incomplete
    text: Incomplete
    contentpath: Incomplete
    position: Incomplete
    created_at: Incomplete
    updated_at: Incomplete
    revision_created: Incomplete
    resolved_at: Incomplete
    resolved_by: Incomplete
    class Meta:
        verbose_name: Incomplete
        verbose_name_plural: Incomplete
    def save(self, update_position: bool = False, **kwargs): ...  # type: ignore
    def log_create(self, **kwargs) -> None: ...
    def log_edit(self, **kwargs) -> None: ...
    def log_resolve(self, **kwargs) -> None: ...
    def log_delete(self, **kwargs) -> None: ...
    def has_valid_contentpath(self, page):
        """
        Return True if this comment's contentpath corresponds to a valid field or
        StreamField block on the given page object
        """

class CommentReply(models.Model):
    comment: Incomplete
    user: Incomplete
    text: Incomplete
    created_at: Incomplete
    updated_at: Incomplete
    class Meta:
        verbose_name: Incomplete
        verbose_name_plural: Incomplete
    def log_create(self, **kwargs) -> None: ...
    def log_edit(self, **kwargs) -> None: ...
    def log_delete(self, **kwargs) -> None: ...

class PageSubscription(models.Model):
    user: Incomplete
    page: Incomplete
    comment_notifications: Incomplete
    wagtail_reference_index_ignore: bool
    class Meta:
        unique_together: Incomplete
