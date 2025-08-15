from __future__ import annotations

from typing import TYPE_CHECKING, Any, Unpack

from django.conf import settings
from django.db.models import Model
from modeltrans.utils import build_localized_fieldname
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel

if TYPE_CHECKING:
    from wagtail.admin.panels.field_panel import WidgetOverrideType
    from wagtail.admin.panels.group import PanelGroupInitArgs


class TranslatedLanguagePanel(FieldPanel):
    main_field_name: str
    language: str

    def __init__(self, field_name: str, language: str, **kwargs):
        self.main_field_name = field_name
        self.language = language
        field_name = build_localized_fieldname(field_name, language.lower(), default_language='')
        super().__init__(field_name, **kwargs)

    def clone_kwargs(self):
        ret = super().clone_kwargs()
        ret['field_name'] = self.main_field_name
        ret['language'] = self.language
        return ret

    class BoundPanel(FieldPanel.BoundPanel):
        panel: TranslatedLanguagePanel

        def is_shown(self):
            from paths.context import realm_context
            instance = realm_context.get().realm
            ret = super().is_shown()
            if not ret:
                return False
            is_other_lang = self.panel.language in (instance.other_languages or [])
            return is_other_lang


class TranslatedFieldRowPanel[M: Model, P: Any](FieldRowPanel[M, P]):
    def __init__(self, field_name: str, widget: WidgetOverrideType | None = None, **kwargs: Unpack[PanelGroupInitArgs]):
        self.field_name = field_name
        self.widget = widget
        primary_panel = FieldPanel(field_name, widget=widget, **kwargs)
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
        primary_panel = FieldPanel(field_name, widget=widget, **kwargs)
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
