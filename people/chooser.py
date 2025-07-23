from __future__ import annotations

from django.contrib.admin.utils import quote
from django.urls import reverse
from wagtail.admin.ui.tables import Column, TitleColumn


class BasePersonChooseViewMixin:
    """
    Base for mixins for subclasses of Wagtail's `BaseChooseView`.

    You'll want to override some additional methods of that view, such as `get_object_list()`.
    """

    chosen_url_name: str

    ordering = ('last_name', 'first_name')

    @property
    def columns(self):
        link_kwargs = {
            'get_url': (
                lambda obj: self.append_preserved_url_parameters(  # type: ignore
                    reverse(self.chosen_url_name, args=(quote(obj.pk),))
                )
            ),
            'link_attrs': {'data-chooser-modal-choice': True},
        }
        return [
            TitleColumn('first_name', **link_kwargs),
            TitleColumn('last_name', **link_kwargs),
            TitleColumn('email', **link_kwargs),
            Column('title'),
            Column('organization'),
        ]
