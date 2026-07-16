from django.conf import settings
from django.db import models


class SystemLog(models.Model):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='system_logs',
    )
    action = models.CharField(max_length=255)
    target_report_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.action} — {self.created_at:%Y-%m-%d %H:%M}"