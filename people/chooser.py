from __future__ import annotations

from typing import TYPE_CHECKING

from django.forms.models import modelform_factory
from django.utils.translation import gettext_lazy as _

from dal import autocomplete
from generic_chooser.views import ModelChooserCreateTabMixin, ModelChooserMixin, ModelChooserViewSet
from generic_chooser.widgets import AdminChooser

from people.models import Person, PersonQuerySet

if TYPE_CHECKING:
    from django.http.request import HttpRequest


class PersonChooserMixin(ModelChooserMixin[Person, PersonQuerySet]):
    request: HttpRequest

    def get_unfiltered_object_list(self) -> PersonQuerySet:
        objects = self.model.objects.get_queryset()
        if self.order_by:
            objects = objects.order_by('last_name', 'first_name')
        return objects

    def get_row_data(self, item):
        avatar_url = item.get_avatar_url(self.request, '50x50')
        return {
            'choose_url': self.get_chosen_url(item),
            'name': self.get_object_string(item),
            'title': item.title,
            'organization': item.organization,
            'avatar_url': avatar_url,
        }

    def get_results_template(self):
        return 'kausal_common/people/chooser_results.html'


class PersonModelChooserCreateTabMixin(ModelChooserCreateTabMixin[Person]):
    model: type[Person]
    create_tab_label = _("Create new")

    def get_form_class(self):
        if self.form_class:
            return self.form_class

        organization_widget = autocomplete.ModelSelect2(url='organization-autocomplete')

        self.form_class = modelform_factory(self.model, fields=self.fields, widgets=dict(
            organization=organization_widget,
        ))
        return self.form_class


class PersonChooserViewSet(ModelChooserViewSet[Person]):
    icon = 'user'
    model = Person
    page_title = _("Choose person")
    per_page = 10
    order_by = ('last_name', 'first_name')
    fields = ['first_name', 'last_name', 'email', 'title', 'organization']


class PersonChooser(AdminChooser):
    choose_one_text = _('Choose a person')
    choose_another_text = _('Choose another person')
    link_to_chosen_text = _('Edit this person')
    model = Person
    choose_modal_url_name = 'person_chooser:choose'

