from .base import ImageBackend as ImageBackend
from _typeshed import Incomplete

class EasyThumbnailsBackend(ImageBackend):
    exceptions_to_catch: Incomplete
    def get_thumbnail_url(self, image_path, thumbnail_options): ...
    def get_size(self, image): ...
