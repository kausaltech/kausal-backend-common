from .utils import get_backend as get_backend

class ImageCroppingMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs): ...
