from collections.abc import Sequence
from typing import ClassVar, Generic, Self
from typing_extensions import TypeVar

from django.core.checks import CheckMessage
from django.db import migrations, models
from django.db.models import Model
from django.db.models.fields import CharField
from wagtail.actions.copy_for_translation import CopyForTranslationAction as CopyForTranslationAction
from wagtail.coreutils import (
    get_content_languages as get_content_languages,
    get_supported_content_language_variant as get_supported_content_language_variant,
)
from wagtail.models import _copy_signature
from wagtail.signals import pre_validate_delete as pre_validate_delete

from _typeshed import Incomplete

class LocaleManager(models.Manager[Locale]):
    def get_for_language(self, language_code: str) -> Locale:
        """
        Gets a Locale from a language code.
        """

class Locale(models.Model):
    language_code: CharField[str, str]
    objects: ClassVar[LocaleManager]  # pyright: ignore
    all_objects: ClassVar[models.Manager[Locale]]

    @classmethod
    def get_default(cls) -> Locale:
        """
        Returns the default Locale based on the site's LANGUAGE_CODE setting
        """
    @classmethod
    def get_active(cls) -> Locale:
        """
        Returns the Locale that corresponds to the currently activated language in Django.
        """

    @_copy_signature(Model.delete)
    def delete(self, *args, **kwargs): ...
    def language_code_is_valid(self) -> bool: ...
    def get_display_name(self) -> str: ...
    @property
    def language_info(self) -> dict: ...
    @property
    def language_name(self) -> str:
        '''
        Uses data from ``django.conf.locale`` to return the language name in
        English. For example, if the object\'s ``language_code`` were ``"fr"``,
        the return value would be ``"French"``.

        Raises ``KeyError`` if ``django.conf.locale`` has no information
        for the object\'s ``language_code`` value.
        '''
    @property
    def language_name_local(self) -> str:
        '''
        Uses data from ``django.conf.locale`` to return the language name in
        the language itself. For example, if the ``language_code`` were
        ``"fr"`` (French), the return value would be ``"français"``.

        Raises ``KeyError`` if ``django.conf.locale`` has no information
        for the object\'s ``language_code`` value.
        '''
    @property
    def language_name_localized(self) -> str:
        '''
        Uses data from ``django.conf.locale`` to return the language name in
        the currently active language. For example, if ``language_code`` were
        ``"fr"`` (French), and the active language were ``"da"`` (Danish), the
        return value would be ``"Fransk"``.

        Raises ``KeyError`` if ``django.conf.locale`` has no information
        for the object\'s ``language_code`` value.

        '''
    @property
    def is_bidi(self) -> bool:
        """
        Returns a boolean indicating whether the language is bi-directional.
        """
    @property
    def is_default(self) -> bool:
        """
        Returns a boolean indicating whether this object is the default locale.
        """
    @property
    def is_active(self) -> bool:
        """
        Returns a boolean indicating whether this object is the currently active locale.
        """

_QS = TypeVar('_QS', bound=models.QuerySet, default=models.QuerySet, covariant=True)  # noqa: PLC0105


class TranslatableMixin(Generic[_QS], models.Model):
    translation_key: models.UUIDField
    locale: models.ForeignKey[Locale, Locale]

    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]: ...
    @property
    def localized(self) -> Self:
        """
        Finds the translation in the current active language.

        If there is no translation in the active language, self is returned.

        Note: This will not return the translation if it is in draft.
        If you want to include drafts, use the ``.localized_draft`` attribute instead.
        """
    @property
    def localized_draft(self) -> Self:
        """
        Finds the translation in the current active language.

        If there is no translation in the active language, self is returned.

        Note: This will return translations that are in draft. If you want to exclude
        these, use the ``.localized`` attribute.
        """
    def get_translations(self, inclusive: bool = False) -> _QS:
        """
        Returns a queryset containing the translations of this instance.
        """
    def get_translation(self, locale: Locale) -> Self:
        """
        Finds the translation in the specified locale.

        If there is no translation in that locale, this raises a ``model.DoesNotExist`` exception.
        """
    def get_translation_or_none(self, locale: Locale) -> Self | None:
        """
        Finds the translation in the specified locale.

        If there is no translation in that locale, this returns None.
        """
    def has_translation(self, locale: Locale) -> bool:
        """
        Returns True if a translation exists in the specified locale.
        """
    def copy_for_translation(self, locale: Locale, *, exclude_fields: Sequence[str] | None = None) -> Self:
        """
        Creates a copy of this instance with the specified locale.

        Note that the copy is initially unsaved.
        """
    def get_default_locale(self) -> Locale:
        """
        Finds the default locale to use for this object.

        This will be called just before the initial save.
        """
    @classmethod
    def get_translation_model(cls) -> type[Model]:
        '''
        Returns this model\'s "Translation model".

        The "Translation model" is the model that has the ``locale`` and
        ``translation_key`` fields.
        Typically this would be the current model, but it may be a
        super-class if multi-table inheritance is in use (as is the case
        for ``wagtailcore.Page``).
        '''

def bootstrap_translatable_model(model, locale) -> None:
    '''
    This function populates the "translation_key", and "locale" fields on model instances that were created
    before wagtail-localize was added to the site.

    This can be called from a data migration, or instead you could use the "bootstrap_translatable_models"
    management command.
    '''

class BootstrapTranslatableModel(migrations.RunPython):
    def __init__(self, model_string, language_code: Incomplete | None = None) -> None: ...

class BootstrapTranslatableMixin(TranslatableMixin):
    """
    A version of TranslatableMixin without uniqueness constraints.

    This is to make it easy to transition existing models to being translatable.

    The process is as follows:
     - Add BootstrapTranslatableMixin to the model
     - Run makemigrations
     - Create a data migration for each app, then use the BootstrapTranslatableModel operation in
       wagtail.models on each model in that app
     - Change BootstrapTranslatableMixin to TranslatableMixin
     - Run makemigrations again
     - Migrate!
    """
    translation_key: Incomplete
    locale: Incomplete
    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]: ...
    class Meta:  # noqa: DJ012
        abstract: bool

def get_translatable_models(include_subclasses: bool = False) -> list[type[Model]]:
    """
    Returns a list of all concrete models that inherit from TranslatableMixin.
    By default, this only includes models that are direct children of TranslatableMixin,
    to get all models, set the include_subclasses attribute to True.
    """
def set_locale_on_new_instance(sender, instance, **kwargs) -> None: ...
