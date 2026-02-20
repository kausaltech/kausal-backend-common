from __future__ import annotations

import typing
import uuid
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Self, override

from django.conf import settings
from django.contrib import admin
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modeltrans.fields import TranslationField
from modeltrans.manager import MultilingualQuerySet
from wagtail.fields import RichTextField
from wagtail.search import index

from treebeard.mp_tree import MP_Node, MP_NodeQuerySet

from kausal_common.models.language import ModelWithPrimaryLanguage

from ..i18n.helpers import get_supported_languages

if TYPE_CHECKING:
    from users.models import User

    from ..models.types import FK


# TODO: Generalize and put in some other app's models.py
class Node[QS: MP_NodeQuerySet[Any]](MP_Node[QS], ClusterableModel):
    class Meta:
        abstract = True

    name = models.CharField[str, str](max_length=255, verbose_name=_("name"))

    # Disabled `node_order_by` for now. If we used this, then we wouldn't be able to use "left sibling" to specify a
    # position of a node, e.g., when calling the REST API from the grid editor. Since it would be significant work to
    # change it (e.g., disable move handles in grid editor, distinguish cases in the backend whether model has
    # node_order_by, etc.) and some customers might want to order their organizations in some way, I decided to disable
    # `node_order_by`.
    # node_order_by = ['name']

    public_fields = ['id', 'name']

    # Duplicate get_parent from super class just to set short_description below
    @admin.display(
        description=pgettext_lazy('node', 'Parent'),
    )
    def get_parent(self, *args, **kwargs) -> Self | None:
        return super().get_parent(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    @property
    def tree_label(self) -> str:
        return self.name

    def get_parent_path(self, update=False) -> str | None:
        depth = int(len(self.path) / self.steplen)
        if depth <= 1:
            return None
        parentpath = self._get_basepath(self.path, depth - 1)
        return parentpath

class BaseOrganizationClass(models.Model):
    identifier = models.CharField(max_length=255, unique=True, editable=False)
    name = models.CharField(max_length=255)

    created_time = models.DateTimeField(auto_now_add=True,
                                        help_text=_('The time at which the resource was created'))
    last_modified_time = models.DateTimeField(auto_now=True,
                                              help_text=_('The time at which the resource was updated'))

    i18n = TranslationField(fields=('name',))

    public_fields: typing.ClassVar = ['id', 'identifier', 'name', 'created_time', 'last_modified_time']

    class Meta:
        # FIXME: Probably we can't rely on this with i18n
        ordering = ['name']
        abstract = True

    def __str__(self):
        return self.name


class BaseOrganizationQuerySet[M: models.Model](MP_NodeQuerySet[M], MultilingualQuerySet[M]):  # type: ignore[override]
    def editable_by_user(self, user: User):  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError('This method should be implemented by subclasses')


if TYPE_CHECKING:
    class TreeModel(MP_Node[Any]): ...
else:
    class TreeModel: ...


class BaseOrganization(index.Indexed, TreeModel, ModelWithPrimaryLanguage, gis_models.Model):
    # Different identifiers, depending on origin (namespace), are stored in OrganizationIdentifier

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    classification = models.ForeignKey(
        'orgs.OrganizationClass',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name=pgettext_lazy('organization', 'Classification'),
        help_text=_('An organization category (e.g., committee)'),
    )
    # TODO: Check if we can / should remove this since already `Node` specifies `name`
    name = models.CharField[str, str](
        max_length=255,
        verbose_name=_('name'),
        help_text=_('Full name of the organization'),
    )
    abbreviation = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=pgettext_lazy('organization', 'short name'),
        help_text=_(
            'Short version or abbreviation of the organization name to be displayed when it is not necessary to show '
            'the full name'
        ),
    )
    distinct_name = models.CharField(
        max_length=400,
        editable=False,
        null=True,
        verbose_name=pgettext_lazy('organization', 'distinct name'),
        help_text=_('A distinct name for this organization (generated automatically)'),
    )
    description = RichTextField(blank=True, verbose_name=_('description'))
    url = models.URLField(blank=True, verbose_name=_('URL'))
    email = models.EmailField(blank=True, verbose_name=_('email address'))
    founding_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=pgettext_lazy('organization', 'founding date'),
    )
    dissolution_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=pgettext_lazy('organization', 'dissolution date'),
    )
    created_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at'),
        help_text=_('The time at which the object for this organization was created'),
    )
    created_by: FK[User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_organizations',
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        verbose_name=_('created by'),
    )
    last_modified_time = models.DateTimeField(
        auto_now=True,
        verbose_name=_('updated at'),
        help_text=_('The time at which the object for this organization was last updated'),
    )
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='modified_organizations',
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        verbose_name=_('updated by'),
    )

    # Intentionally overrides ModelWithPrimaryLanguage.primary_language
    # leaving out the default keyword argument
    primary_language = models.CharField(
        max_length=8, choices=get_supported_languages, verbose_name=_('primary language'),
    )
    location = gis_models.PointField(verbose_name=_('location'), srid=4326, null=True, blank=True)

    i18n = TranslationField(fields=('name', 'abbreviation'), default_language_field='primary_language_lowercase')

    public_fields: ClassVar[list[str]] = ['id', 'uuid', 'name', 'abbreviation', 'parent']

    search_fields = [
        index.AutocompleteField('name'),
        index.AutocompleteField('abbreviation'),
        index.SearchField('name'),
        index.SearchField('abbreviation'),
    ]


    id: int
    classification_id: int | None

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        abstract = True

    @property
    def parent(self) -> Self | None:
        return self.get_parent()

    @classmethod
    def get_parent_choices(cls, user: User, obj: Self | None = None) -> models.QuerySet[Self]:
        raise NotImplementedError('This method should be implemented by subclasses')

    @override
    def __str__(self):
        return self.name

    def __rich_repr__(self):
        yield 'id', self.pk
        yield 'name', self.name
        if self.abbreviation:
            yield 'abbreviation', self.abbreviation
        yield 'uuid', str(self.uuid)
        if self.parent:
            yield 'parent', self.parent.name
        if self.classification:
            yield 'classification', self.classification.name


class BaseNamespace(models.Model):
    identifier = models.CharField(max_length=255, unique=True, editable=False)
    name = models.CharField(max_length=255)
    user_editable = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.name} ({self.identifier})'


class BaseOrganizationIdentifier(models.Model):
    organization = ParentalKey('orgs.Organization', on_delete=models.CASCADE, related_name='identifiers')
    identifier = models.CharField(max_length=255)
    namespace = models.ForeignKey('orgs.Namespace', on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['namespace', 'identifier'], name='unique_identifier_in_namespace'),
        ]
        abstract = True

    def __str__(self):
        return f'{self.identifier} @ {self.namespace.name}'
