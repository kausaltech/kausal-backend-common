from typing import Any

from wagtail.admin.panels import FieldPanel


class SuperuserOnlyFieldPanel(FieldPanel):
    """A field panel that is writable and visible only to superusers."""

    class BoundPanel(FieldPanel.BoundPanel):
        def __init__(self, **kwargs: Any):
            super().__init__(**kwargs)
            if self.request is not None and not self.request.user.is_superuser and self.bound_field is not None:
                self.bound_field.field.disabled = True

        def is_shown(self) -> bool:
            return bool(super().is_shown() and self.request is not None and self.request.user.is_superuser)
