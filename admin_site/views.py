from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from django.views.generic.base import RedirectView


class RootRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        admin_home_path = reverse('wagtailadmin_home')
        admin_base: str = settings.ADMIN_BASE_URL
        return urljoin(admin_base, admin_home_path)
