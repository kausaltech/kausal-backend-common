from .utils import get_backend as get_backend
from _typeshed import Incomplete
from django.contrib.admin.widgets import AdminFileWidget, ForeignKeyRawIdWidget

logger: Incomplete

def thumbnail_url(image_path): ...
def get_attrs(image, name): ...

class CropWidget:
    media: Incomplete

class ImageCropWidget(AdminFileWidget, CropWidget):
    def render(self, name, value, attrs: Incomplete | None = None, renderer: Incomplete | None = None): ...

class HiddenImageCropWidget(ImageCropWidget):
    def render(self, name, value, attrs: Incomplete | None = None, renderer: Incomplete | None = None): ...

class CropForeignKeyWidget(ForeignKeyRawIdWidget, CropWidget):
    field_name: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    def render(self, name, value, attrs: Incomplete | None = None, renderer: Incomplete | None = None): ...
