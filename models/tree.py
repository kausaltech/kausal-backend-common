from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db.models import Min
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

if TYPE_CHECKING:
    from treebeard.mp_tree import MP_Node, MP_NodeQuerySet


def get_indented_name(obj: MP_Node[Any], indentation_start_depth: int = 2, html: bool = False) -> str | SafeString:
    """
    Render this objects's name as a formatted string that displays its hierarchical depth via indentation.

    If indentation_start_depth is supplied, the models's depth is rendered relative to that depth.
    indentation_start_depth defaults to 2, the depth of the first non-Root model.
    Pass html=True to get an HTML representation, instead of the default plain-text.

    Example text output: "    ↳ Pies"
    Example HTML output: "&nbsp;&nbsp;&nbsp;&nbsp;&#x21b3 Pies"
    """

    obj_name = getattr(obj, 'name', str(obj))

    display_depth = obj.depth - indentation_start_depth
    # A Collection with a display depth of 0 or less (Root's can be -1), should have no indent.
    if display_depth <= 0:
        return obj_name

    # Indent each level of depth by 4 spaces (the width of the ↳ character in our admin font), then add ↳
    # before adding the name.
    if html:
        # NOTE: &#x21b3 is the hex HTML entity for ↳.
        return format_html(
            '{indent}{icon} {name}',
            indent=mark_safe('&nbsp;' * 4 * display_depth),  # noqa: S308
            icon=mark_safe('&#x21b3'),
            name=obj_name,
        )
    # Output unicode plain-text version
    return '{}↳ {}'.format(' ' * 4 * display_depth, obj_name)


def get_min_depth(qs: MP_NodeQuerySet) -> int:
    return qs.aggregate(Min('depth'))['depth__min'] or 2


def get_indented_choices(qs: MP_NodeQuerySet) -> list[tuple[int, str]]:
    """
    Return a list of (id, label) tuples for use as a list of choices.

    The label is formatted with get_indented_name to provide a tree layout.
    The indent level is chosen to place the minimum-depth node at indent 0.
    """
    min_depth = get_min_depth(qs)
    return [(obj.pk, get_indented_name(obj, min_depth, html=True)) for obj in qs]


# TODO: Add this back in when we have a use case for it
# class SelectWithDisabledOptions(forms.Select):
#     """Subclass of Django's select widget that allows disabling options."""

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.disabled_values = ()

#     def create_option(self, name, value, *args, **kwargs):
#         option_dict = super().create_option(name, value, *args, **kwargs)
#         if value in self.disabled_values:
#             option_dict["attrs"]["disabled"] = "disabled"
#         return option_dict
# class MPNodeChoiceField[M: MP_Node](forms.ModelChoiceField[M]):
#     widget = SelectWithDisabledOptions

#     def __init__(self, *args, disabled_queryset=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._indentation_start_depth = 2
#         self.disabled_queryset = disabled_queryset

#     def _get_disabled_queryset(self) -> MP_NodeQuerySet:
#         return self._disabled_queryset

#     def _set_disabled_queryset(self, queryset: MP_NodeQuerySet) -> None:
#         self._disabled_queryset = queryset
#         if queryset is None:
#             self.widget.disabled_values = ()
#         else:
#             self.widget.disabled_values = queryset.values_list(
#                 self.to_field_name or "pk", flat=True
#             )

#     disabled_queryset = property(_get_disabled_queryset, _set_disabled_queryset)

#     def _set_queryset(self, queryset: MP_NodeQuerySet) -> None:
#         min_depth = get_min_depth(queryset)
#         if min_depth is None:
#             self._indentation_start_depth = 2
#         else:
#             self._indentation_start_depth = min_depth + 1

#     def label_from_instance(self, obj: MP_Node) -> str | SafeString:
#         return get_indented_name(obj, self._indentation_start_depth, html=True)


# class MPNodeForm[M: MP_Node](forms.ModelForm[M]):
#     parent = MPNodeChoiceField[M](
#         label=gettext_lazy("Parent"),
#         required=True,
#         help_text=gettext_lazy(
#             "Select hierarchical position. Note: a collection cannot become a child of itself or one of its "
#             "descendants."
#         ),
#     )

#     def clean_parent(self) -> M:
#         # Our rules about where a user may add or move a collection are as follows:
#         #     1. The user must wave 'add' permission on the parent collection (or its ancestors)
#         #     2. We are not moving a collection used to assign permissions for this user
#         #     3. We are not trying to move a collection to be parented by one of their descendants

#         # The first 2 items are taken care in the Create and Edit views by deleting the 'parent' field
#         # from the edit form if the user cannot move the collection. This causes Django's form
#         # machinery to ignore the parent field for parent regardless of what the user submits.
#         # This methods enforces rule #3 when we are editing an existing collection.
#         parent = self.cleaned_data["parent"]
#         if not self.instance._state.adding and parent.pk != self.initial.get("parent"):
#             old_descendants = list(self.instance.get_tree(parent=self.instance).values_list('pk', flat=True))
#             if parent.pk in old_descendants:
#                 raise ValidationError(gettext_lazy("Please select another parent"))
#         return parent
