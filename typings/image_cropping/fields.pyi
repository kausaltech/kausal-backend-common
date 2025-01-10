from .utils import get_backend as get_backend, max_cropping as max_cropping
from .widgets import ImageCropWidget as ImageCropWidget
from _typeshed import Incomplete
from django.db import models

class ImageCropField(models.ImageField):
    def formfield(self, **kwargs): ...  # type: ignore[override]

class ImageRatioField(models.CharField):
    free_crop: Incomplete
    adapt_rotation: Incomplete
    allow_fullsize: Incomplete
    size_warning: Incomplete
    hide_image_field: Incomplete
    box_max_width: Incomplete
    box_max_height: Incomplete
    width: int
    height: int
    def __init__(self, image_field, size: str = '0x0', free_crop: bool = False, adapt_rotation: bool = False, allow_fullsize: bool = False, verbose_name: Incomplete | None = None, help_text: Incomplete | None = None, hide_image_field: bool = False, size_warning=...) -> None: ...
    def deconstruct(self): ...
    def contribute_to_class(self, cls, name, **kwargs) -> None: ...  # type: ignore[override]
    def initial_cropping(self, sender, instance, *args, **kwargs): ...
    def formfield(self, **kwargs): ...  # type: ignore[override]
