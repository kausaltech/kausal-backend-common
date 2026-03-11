from django.db import models

from _typeshed import Incomplete
from wagtail_color_panel.validators import hex_triplet_validator as hex_triplet_validator

class ColorField(models.CharField):
    default_validators: Incomplete
    description: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
