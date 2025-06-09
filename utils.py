from django.conf import settings
def get_supported_languages():
    yield from settings.LANGUAGES