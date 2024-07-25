from wagtail.admin.utils import get_latest_str as get_latest_str
from wagtail.admin.views.generic.base import BaseOperationView as BaseOperationView
from wagtail.log_actions import log as log

class LockView(BaseOperationView):
    success_message_extra_tags: str
    def perform_operation(self) -> None: ...

class UnlockView(BaseOperationView):
    success_message_extra_tags: str
    def perform_operation(self) -> None: ...
    def get_success_message(self): ...
