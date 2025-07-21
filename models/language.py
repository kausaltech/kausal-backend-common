from django.db import models

from kausal_common.i18n.helpers import get_default_language, get_default_language_lowercase, get_supported_languages

LANGUAGE_MAX_LENGTH = 8

class ModelWithPrimaryLanguage(models.Model):
    primary_language = models.CharField(
        max_length=LANGUAGE_MAX_LENGTH, choices=get_supported_languages(), default=get_default_language,
    )

    # The lowercase field must be used as the modeltrans default language field instead of the primary language field itself,
    # because modeltrans is using lowercase language codes. Otherwise primary languages with variant suffixes do not match,
    # causing all sorts of problems.
    primary_language_lowercase =  models.CharField(max_length=LANGUAGE_MAX_LENGTH, default=get_default_language_lowercase)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.primary_language_lowercase = self.primary_language.lower()
        super().save(*args, **kwargs)
