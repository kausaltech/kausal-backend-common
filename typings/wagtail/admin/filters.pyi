import django_filters
from _typeshed import Incomplete
from django.utils.functional import cached_property as cached_property
from django_filters.widgets import SuffixedMultiWidget
from wagtail.admin.models import popular_tags_for_model as popular_tags_for_model
from wagtail.admin.utils import get_user_display_name as get_user_display_name
from wagtail.admin.widgets import (
    AdminDateInput as AdminDateInput,
    BooleanRadioSelect as BooleanRadioSelect,
    FilteredSelect as FilteredSelect,
)
from wagtail.coreutils import get_content_languages as get_content_languages, get_content_type_label as get_content_type_label

class DateRangePickerWidget(SuffixedMultiWidget):
    template_name: str
    suffixes: Incomplete
    def __init__(self, attrs: Incomplete | None = None) -> None: ...
    def decompress(self, value): ...

class FilteredModelChoiceIterator(django_filters.fields.ModelChoiceIterator):
    def choice(self, obj): ...

class FilteredModelChoiceField(django_filters.fields.ModelChoiceField):
    widget = FilteredSelect
    iterator = FilteredModelChoiceIterator
    filter_accessor: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    def get_filter_value(self, obj): ...

class FilteredModelChoiceFilter(django_filters.ModelChoiceFilter):
    field_class = FilteredModelChoiceField

class LocaleFilter(django_filters.ChoiceFilter):
    def filter(self, qs, language_code): ...

class WagtailFilterSet(django_filters.FilterSet):
    def __init__(self, data: Incomplete | None = None, queryset: Incomplete | None = None, *, request: Incomplete | None = None, prefix: Incomplete | None = None) -> None: ...
    @classmethod
    def filter_for_lookup(cls, field, lookup_type): ...

class ContentTypeModelChoiceField(django_filters.fields.ModelChoiceField):
    def label_from_instance(self, obj): ...

class ContentTypeFilter(django_filters.ModelChoiceFilter):
    field_class = ContentTypeModelChoiceField

class ContentTypeModelMultipleChoiceField(django_filters.fields.ModelMultipleChoiceField):
    def label_from_instance(self, obj): ...

class MultipleContentTypeFilter(django_filters.ModelMultipleChoiceFilter):
    field_class = ContentTypeModelMultipleChoiceField

class UserModelMultipleChoiceField(django_filters.fields.ModelMultipleChoiceField):
    def label_from_instance(self, obj): ...

class MultipleUserFilter(django_filters.ModelMultipleChoiceFilter):
    field_class = UserModelMultipleChoiceField

class CollectionChoiceIterator(django_filters.fields.ModelChoiceIterator):
    @cached_property
    def min_depth(self): ...
    def choice(self, obj): ...

class CollectionChoiceField(django_filters.fields.ModelChoiceField):
    iterator = CollectionChoiceIterator

class CollectionFilter(django_filters.ModelChoiceFilter):
    field_class = CollectionChoiceField

class PopularTagsFilter(django_filters.MultipleChoiceFilter):
    use_subquery: Incomplete
    def __init__(self, *args, use_subquery: bool = False, **kwargs) -> None: ...
    def filter(self, qs, value): ...

class BaseMediaFilterSet(WagtailFilterSet):
    permission_policy: Incomplete
    def __init__(self, data: Incomplete | None = None, queryset: Incomplete | None = None, *, request: Incomplete | None = None, prefix: Incomplete | None = None, is_searching: Incomplete | None = None) -> None: ...
