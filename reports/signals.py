from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Report, ReportTimeline
from .services import ReportService


@receiver(post_save, sender=Report)
def create_initial_timeline(sender, instance, created, **kwargs):
    if created and not instance.timeline.exists():
        ReportService.create_timeline(instance, status=instance.status, note='Report created.', updated_by=instance.reporter)
