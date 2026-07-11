from django.contrib import admin

from .models import CrimeType, Evidence, Notification, Report, ReportTimeline


@admin.register(CrimeType)
class CrimeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    ordering = ('name',)


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'crime_type', 'status', 'priority', 'anonymous', 'reporter', 'created_at')
    list_filter = ('status', 'priority', 'anonymous', 'crime_type')
    search_fields = ('tracking_code', 'address', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('tracking_code', 'created_at', 'updated_at')
    inlines = [EvidenceInline]


@admin.register(ReportTimeline)
class ReportTimelineAdmin(admin.ModelAdmin):
    list_display = ('report', 'status', 'updated_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('report__tracking_code', 'note')
    ordering = ('-created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('title', 'message')
    ordering = ('-created_at',)
