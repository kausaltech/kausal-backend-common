from __future__ import annotations

from typing import TYPE_CHECKING

from modeltrans.conf import get_available_languages
from modeltrans.translator import get_i18n_field
from modeltrans.utils import build_localized_fieldname
from wagtail.admin.forms import WagtailAdminModelForm

from .helpers import get_language_from_default_language_field, convert_language_code

if TYPE_CHECKING:
    from django.db.models import Model

    from modeltrans.fields import TranslationField


class LanguageAwareAdminModelForm[ModelT: Model](WagtailAdminModelForm[ModelT]):
    realm_initialized: bool = False

    def get_languages_to_show(self, i18n_field: TranslationField) -> set[str]:
        """
        Return a list of languages we want to display translation fields for.

        This includes other languages of the plan, but also the
        primary language of the plan, if it's different from the
        primary language of the current model being edited.

        It does not include the original language field without
        the language suffix, since that field is added to the
        form separately.

        Please note: it is not enough nor necessary to hide the
        language variant panels with is_shown since we have to
        remove the form fields here anyway in order for the
        form to be validated correctly.
        """

        original_field_language = self.get_primary_realm_language()
        languages_to_show: set[str] = self.get_all_realm_languages()

        if i18n_field.default_language_field:
            original_field_language = get_language_from_default_language_field(self.instance, i18n_field)
            original_field_language = convert_language_code(original_field_language, 'django')

        # In the end, we make sure the modeltrans original field -- ie. the field
        # without the language suffix which is saved directly to the original db
        # field and not in the i18n field -- is never shown twice (once here and once as the
        # PrimaryLanguagePanel which was added as a separate panel.
        if original_field_language in languages_to_show:
            languages_to_show.remove(original_field_language)
        return languages_to_show

    def prune_i18n_fields(self):
        i18n_field: TranslationField | None = get_i18n_field(self._meta.model)
        if not i18n_field:
            return
        languages_to_show = self.get_languages_to_show(i18n_field)
        for base_field_name in i18n_field.fields:
            langs = list(get_available_languages(include_default=True))
            for lang in langs:
                fn = build_localized_fieldname(base_field_name, lang)
                if lang not in languages_to_show and fn in self.fields:
                    del self.fields[fn]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.realm_initialized:
            self.prune_i18n_fields()

    def get_primary_realm_language(self) -> str:
        raise NotImplementedError()

    def get_all_realm_languages(self) -> set[str]:
        raise NotImplementedError()
