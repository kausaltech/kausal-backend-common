"""
This type stub file was generated by pyright.
"""

from django.conf import settings

"""
Settings for Graphene are all namespaced in the GRAPHENE setting.
For example your project's `settings.py` file might look like this:
GRAPHENE = {
    'SCHEMA': 'my_app.schema.schema'
    'MIDDLEWARE': (
        'graphene_django.debug.DjangoDebugMiddleware',
    )
}
This module provides the `graphene_settings` object, that is used to access
Graphene settings, checking for user settings first, then falling
back to the defaults.
"""
DEFAULTS = ...
if settings.DEBUG:
    ...
IMPORT_STRINGS = ...
def perform_import(val, setting_name): # -> Any | list[Any] | None:
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    ...

def import_from_string(val, setting_name): # -> Any:
    """
    Attempt to import a class from a string representation.
    """
    ...

class GrapheneSettings:
    """
    A settings object, that allows API settings to be accessed as properties.
    For example:
        from graphene_django.settings import settings
        print(settings.SCHEMA)
    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """
    def __init__(self, user_settings=..., defaults=..., import_strings=...) -> None:
        ...
    
    @property
    def user_settings(self): # -> Any | dict[Any, Any]:
        ...
    
    def __getattr__(self, attr): # -> Any | list[Any] | None:
        ...
    


graphene_settings = ...
def reload_graphene_settings(*args, **kwargs): # -> None:
    ...

