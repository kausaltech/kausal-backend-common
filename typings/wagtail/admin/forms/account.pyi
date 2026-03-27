from django import forms
from wagtail.admin.localization import (
    get_available_admin_languages as get_available_admin_languages,
    get_available_admin_time_zones as get_available_admin_time_zones,
)
from wagtail.admin.widgets import SwitchInput as SwitchInput
from wagtail.permissions import page_permission_policy as page_permission_policy
from wagtail.users.models import UserProfile as UserProfile

from _typeshed import Incomplete

User: Incomplete

class NotificationPreferencesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None: ...
    class Meta:
        model = UserProfile
        fields: Incomplete
        widgets: Incomplete

class LocalePreferencesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None: ...
    preferred_language: Incomplete
    current_time_zone: Incomplete
    class Meta:
        model = UserProfile
        fields: Incomplete

class NameEmailForm(forms.ModelForm):
    first_name: Incomplete
    last_name: Incomplete
    email: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    class Meta:
        model = User
        fields: Incomplete

class AvatarPreferencesForm(forms.ModelForm):
    avatar: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    def clean_avatar(self): ...
    def save(self, commit: bool = True): ...
    class Meta:
        model = UserProfile
        fields: Incomplete

class ThemePreferencesForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields: Incomplete
        widgets: Incomplete
