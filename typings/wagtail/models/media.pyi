from collections.abc import Sequence
from typing import ClassVar

from django.db import models
from django.db.models import CharField, ForeignKey, Model
from django_stubs_ext import StrPromise
from wagtail.query import TreeQuerySet as TreeQuerySet
from wagtail.search import index as index

from _typeshed import Incomplete
from treebeard.mp_tree import MP_Node

from .view_restrictions import BaseViewRestriction as BaseViewRestriction

class CollectionQuerySet(TreeQuerySet[Collection]):
    def get_min_depth(self): ...
    def get_indented_choices(self):
        """
        Return a list of (id, label) tuples for use as a list of choices in a collection chooser
        dropdown, where the label is formatted with get_indented_name to provide a tree layout.
        The indent level is chosen to place the minimum-depth collection at indent 0.
        """

class BaseCollectionManager(models.Manager[Collection]):
    def get_queryset(self) -> CollectionQuerySet: ...

class CollectionManager(BaseCollectionManager): ...

class CollectionViewRestriction(BaseViewRestriction):
    collection: models.ForeignKey[Collection, Collection]
    passed_view_restrictions_session_key: str
    class Meta:  # pyright: ignore
        verbose_name: StrPromise
        verbose_name_plural: StrPromise


class Collection(MP_Node[CollectionQuerySet]):
    """
    A location in which resources such as images and documents can be grouped
    """

    name: CharField[str, str]
    objects: ClassVar[CollectionManager]  # type: ignore[assignment]
    node_order_by: list[str]

    def get_ancestors(self, inclusive: bool = False) -> CollectionQuerySet: ...
    def get_descendants(self, inclusive: bool = False) -> CollectionQuerySet: ...
    def get_siblings(self, inclusive: bool = True) -> CollectionQuerySet: ...
    def get_next_siblings(self, inclusive: bool = False) -> CollectionQuerySet: ...
    def get_prev_siblings(self, inclusive: bool = False) -> CollectionQuerySet: ...
    def get_view_restrictions(self):
        """Return a query set of all collection view restrictions that apply to this collection"""
    def get_indented_name(self, indentation_start_depth: int = 2, html: bool = False):
        '''
        Renders this Collection\'s name as a formatted string that displays its hierarchical depth via indentation.
        If indentation_start_depth is supplied, the Collection\'s depth is rendered relative to that depth.
        indentation_start_depth defaults to 2, the depth of the first non-Root Collection.
        Pass html=True to get an HTML representation, instead of the default plain-text.

        Example text output: "    ↳ Pies"
        Example HTML output: "&nbsp;&nbsp;&nbsp;&nbsp;&#x21b3 Pies"
        '''
    class Meta:
        verbose_name: Incomplete
        verbose_name_plural: Incomplete

def get_root_collection_id(): ...

class CollectionMember(models.Model):
    """
    Base class for models that are categorised into collections
    """
    collection: ForeignKey[Collection, Collection]
    search_fields: Sequence[index.BaseField]


class GroupCollectionPermissionManager(models.Manager):
    def get_by_natural_key(self, group, collection, permission): ...


class GroupCollectionPermission(models.Model):
    '''
    A rule indicating that a group has permission for some action (e.g. "create document")
    within a specified collection.
    '''
    group: Incomplete
    collection: Incomplete
    permission: Incomplete
    objects: Incomplete
    class Meta: ...
    def natural_key(self): ...


class UploadedFile(models.Model):
    """
    Temporary storage for media fields uploaded through the multiple image/document uploader.
    When validation rules (e.g. required metadata fields) prevent creating an Image/Document object from the file alone.
    In this case, the file is stored against this model, to be turned into an Image/Document object once the full form
    has been filled in.
    """
    for_content_type: Incomplete
    file: Incomplete
    uploaded_by_user: Incomplete
