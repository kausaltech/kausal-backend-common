import abc
from .. import widgets as widgets
from _typeshed import Incomplete

class ImageBackend(metaclass=abc.ABCMeta):
    exceptions_to_catch: Incomplete
    WIDGETS: Incomplete
    kwargs: Incomplete
    def __init__(self, **kwargs) -> None: ...
    @abc.abstractmethod
    def get_thumbnail_url(self, image_path, thumbnail_options): ...
    @abc.abstractmethod
    def get_size(self, image): ...
    def get_widget(self, db_field, target, admin_site): ...
