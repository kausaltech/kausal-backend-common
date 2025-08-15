from __future__ import annotations

from typing import override, TYPE_CHECKING, Any, Unpack

from django.conf import settings
from django.db.models import Model
from modeltrans.utils import build_localized_fieldname
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel

from kausal_common.i18n.helpers import convert_language_code, get_language_from_default_language_field


if TYPE_CHECKING:
    from wagtail.admin.panels.field_panel import WidgetOverrideType
    from wagtail.admin.panels.group import PanelGroupInitArgs


class PrimaryLanguagePanel(FieldPanel):
    @override
    def get_bound_panel(self, instance=None, request=None, form=None, prefix="panel"):
        bound_panel = super().get_bound_panel(instance, request, form, prefix)
        language = get_language_from_default_language_field(bound_panel.instance)
        bound_panel.heading = f'{bound_panel.heading} ({language.upper()})'
        return bound_panel


class TranslatedLanguagePanel(FieldPanel):
    main_field_name: str
    language: str

    def __init__(self, field_name: str, language: str, **kwargs):
        self.main_field_name = field_name
        self.language = language
        field_name = build_localized_fieldname(field_name, convert_language_code(language, 'modeltrans'), default_language='')
        super().__init__(field_name, **kwargs)

    def clone_kwargs(self):
        ret = super().clone_kwargs()
        ret['field_name'] = self.main_field_name
        ret['language'] = self.language
        return ret


class TranslatedFieldRowPanel[M: Model, P: Any](FieldRowPanel[M, P]):
    def __init__(self, field_name: str, widget: WidgetOverrideType | None = None, **kwargs: Unpack[PanelGroupInitArgs]):
        self.field_name = field_name
        self.widget = widget
        primary_panel = PrimaryLanguagePanel(field_name, widget=widget, **kwargs)
        lang_panels = [TranslatedLanguagePanel(
            field_name=field_name,
            language=lang[0],
            widget=widget,
            **kwargs
        ) for lang in settings.LANGUAGES]
        super().__init__(children=[primary_panel, *lang_panels], **kwargs)

    def clone_kwargs(self):
        ret = super().clone_kwargs()
        del ret['children']
        ret['field_name'] = self.field_name
        ret['widget'] = self.widget
        return ret


class TranslatedFieldPanel(MultiFieldPanel):
    def __init__(self, field_name: str, widget: Any = None, **kwargs):
        self.field_name = field_name
        self.widget = widget
        primary_panel = PrimaryLanguagePanel(field_name, widget=widget, **kwargs)
        lang_panels = [TranslatedLanguagePanel(
            field_name=field_name,
            language=lang[0],
            widget=widget,
            **kwargs
        ) for lang in settings.LANGUAGES]
        super().__init__(children=[primary_panel, *lang_panels], **kwargs)

    def clone_kwargs(self):
        ret = super().clone_kwargs()
        del ret['children']
        ret['field_name'] = self.field_name
        ret['widget'] = self.widget
        return ret
