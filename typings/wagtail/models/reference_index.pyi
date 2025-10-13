from django.db import models
from django.utils.functional import cached_property as cached_property
from wagtail.blocks import StreamBlock as StreamBlock
from wagtail.fields import StreamField as StreamField

from _typeshed import Incomplete

class ReferenceGroups:
    """
    Groups records in a ReferenceIndex queryset by their source object.

    Args:
        qs: (QuerySet[ReferenceIndex]) A QuerySet on the ReferenceIndex model

    Yields:
        A tuple (source_object, references) for each source object that appears
        in the queryset. source_object is the model instance of the source object
        and references is a list of references that occur in the QuerySet from
        that source object.
    """
    qs: Incomplete
    def __init__(self, qs) -> None: ...
    def __iter__(self): ...
    def __len__(self) -> int: ...
    @cached_property
    def is_protected(self): ...
    def count(self):
        """
        Returns the number of rows that will be returned by iterating this
        ReferenceGroups.

        Just calls len(self) internally, this method only exists to allow
        instances of this class to be used in a Paginator.
        """
    def __getitem__(self, key): ...

class ReferenceIndexQuerySet(models.QuerySet[ReferenceIndex]):
    def group_by_source_object(self):
        """
        Returns a ReferenceGroups object for this queryset that will yield
        references grouped by their source instance.
        """

class ReferenceIndex(models.Model):
    """
    Records references between objects for quick retrieval of object usage.

    References are extracted from Foreign Keys, Chooser Blocks in StreamFields, and links in Rich Text Fields.
    This index allows us to efficiently find all of the references to a particular object from all of these sources.
    """
    content_type: Incomplete
    base_content_type: Incomplete
    object_id: Incomplete
    to_content_type: Incomplete
    to_object_id: Incomplete
    model_path: Incomplete
    content_path: Incomplete
    content_path_hash: Incomplete
    objects: Incomplete
    wagtail_reference_index_ignore: bool
    tracked_models: Incomplete
    indexed_models: Incomplete

    @classmethod
    def model_is_indexable(cls, model, allow_child_models: bool = False):
        """
        Returns True if the given model may have outbound references that we would be interested in recording in the index.


        Args:
            model (type): a Django model class
            allow_child_models (boolean): Child models are not indexable on their own. If you are looking at
                                          a child model from the perspective of indexing it through its parent,
                                          set this to True to disable checking for this. Default False.
        """
    @classmethod
    def register_model(cls, model) -> None:
        """
        Registers the model for indexing.
        """
    @classmethod
    def is_indexed(cls, model): ...
    @classmethod
    def create_or_update_for_object(cls, object) -> None:
        """
        Creates or updates ReferenceIndex records for the given object.

        This method will extract any outbound references from the given object
        and insert/update them in the database.

        Note: This method must be called within a `django.db.transaction.atomic()` block.

        Args:
            object (Model): The model instance to create/update ReferenceIndex records for
        """
    @classmethod
    def remove_for_object(cls, object) -> None:
        """
        Deletes all outbound references for the given object.

        Use this before deleting the object itself.

        Args:
            object (Model): The model instance to delete ReferenceIndex records for
        """
    @classmethod
    def get_references_for_object(cls, object):
        """
        Returns all outbound references for the given object.

        Args:
            object (Model): The model instance to fetch ReferenceIndex records for

        Returns:
            A QuerySet of ReferenceIndex records
        """
    @classmethod
    def get_references_to(cls, object):
        """
        Returns all inbound references for the given object.

        Args:
            object (Model): The model instance to fetch ReferenceIndex records for

        Returns:
            A QuerySet of ReferenceIndex records
        """
    @classmethod
    def get_grouped_references_to(cls, object):
        """
        Returns all inbound references for the given object, grouped by the object
        they are found on.

        Args:
            object (Model): The model instance to fetch ReferenceIndex records for

        Returns:
            A ReferenceGroups object
        """
    @cached_property
    def model_name(self):
        """
        The model name of the object from which the reference was extracted.
        For most cases, this is also where the reference exists on the database
        (i.e. ``related_field_model_name``). However, for ClusterableModels, the
        reference is extracted from the parent model.

        Example:
        A relationship between a BlogPage, BlogPageGalleryImage, and Image
        is extracted from the BlogPage model, but the reference is stored on
        on the BlogPageGalleryImage model.
        """
    @cached_property
    def related_field_model_name(self):
        """
        The model name where the reference exists on the database.
        """
    @cached_property
    def on_delete(self): ...
    @cached_property
    def source_field(self):
        """
        The field from which the reference was extracted.
        This may be a related field (e.g. ForeignKey), a reverse related field
        (e.g. ManyToOneRel), a StreamField, or any other field that defines
        extract_references().
        """
    @cached_property
    def related_field(self): ...
    @cached_property
    def reverse_related_field(self): ...
    def describe_source_field(self):
        """
        Returns a string describing the field that this reference was extracted from.

        For StreamField, this returns the label of the block that contains the reference.
        For other fields, this returns the verbose name of the field.
        """
    def describe_on_delete(self):
        """
        Returns a string describing the action that will be taken when the referenced object is deleted.
        """
