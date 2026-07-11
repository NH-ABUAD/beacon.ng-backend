from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .storage import ConfiguredStorage
from .utils import generate_tracking_code
from .validators import validate_coordinate, validate_description


class CrimeType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Crime Types'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Report(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_VERIFIED = 'Verified'
    STATUS_UNDER_INVESTIGATION = 'Under Investigation'
    STATUS_REJECTED = 'Rejected'
    STATUS_RESOLVED = 'Resolved'
    STATUS_CLOSED = 'Closed'

    PRIORITY_LOW = 'Low'
    PRIORITY_MEDIUM = 'Medium'
    PRIORITY_HIGH = 'High'
    PRIORITY_CRITICAL = 'Critical'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_UNDER_INVESTIGATION, 'Under Investigation'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    tracking_code = models.CharField(max_length=12, unique=True, blank=True)
    crime_type = models.ForeignKey(CrimeType, on_delete=models.PROTECT, related_name='reports')
    description = models.TextField()
    incident_datetime = models.DateTimeField(default=timezone.now)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self):
        self.description = validate_description(self.description)
        self.latitude = Decimal(str(validate_coordinate('latitude', self.latitude)))
        self.longitude = Decimal(str(validate_coordinate('longitude', self.longitude)))
        if not self.tracking_code:
            self.tracking_code = generate_tracking_code()

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            while not self.tracking_code or Report.objects.filter(tracking_code=self.tracking_code).exists():
                self.tracking_code = generate_tracking_code()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.tracking_code} - {self.crime_type.name}'


class Evidence(models.Model):
    report = models.ForeignKey(Report, related_name='evidence', on_delete=models.CASCADE)
    file = models.FileField(upload_to='reports/evidence/', storage=ConfiguredStorage())
    file_type = models.CharField(max_length=20, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-uploaded_at',)

    @classmethod
    def get_file_type(cls, filename):
        extension = Path(filename).suffix.lower().lstrip('.')
        if extension in {'jpg', 'jpeg', 'png', 'webp'}:
            return 'image'
        if extension in {'mp4', 'mov', 'avi'}:
            return 'video'
        return 'other'

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if not self.file_type:
            self.file_type = self.get_file_type(self.file.name if self.file else 'unknown')
        if not self.mime_type and self.file:
            self.mime_type = self.file.content_type or 'application/octet-stream'
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        file_path = self.file.name
        super().delete(using=using, keep_parents=keep_parents)
        if file_path:
            self.file.storage.delete(file_path)

    def __str__(self):
        return f'{self.file.name}'


class ReportTimeline(models.Model):
    report = models.ForeignKey(Report, related_name='timeline', on_delete=models.CASCADE)
    status = models.CharField(max_length=30, choices=Report.STATUS_CHOICES)
    note = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='report_updates',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f'{self.report.tracking_code} - {self.status}'


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title
