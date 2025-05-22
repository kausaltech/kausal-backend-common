from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from users.models import User


class BaseLoggedRequest(models.Model):
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=2000)
    raw_request = models.TextField()
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='logged_requests')
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    class Meta:
        abstract = True
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        date_cutoff = timezone.now() - timedelta(days=settings.REQUEST_LOG_MAX_DAYS)
        self.__class__.objects.filter(created_at__lt=date_cutoff).delete()
        return result

    def __str__(self):
        date_str = self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        result = f'{date_str} {self.method} {self.path}'
        if self.user:
            result += f' by {self.user}'
        return result
