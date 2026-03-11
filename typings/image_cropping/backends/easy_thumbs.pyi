from _typeshed import Incomplete

from .base import ImageBackend as ImageBackend

class EasyThumbnailsBackend(ImageBackend):
    exceptions_to_catch: Incomplete
    def get_thumbnail_url(self, image_path, thumbnail_options): ...
    def get_size(self, image): ...
