from django.contrib import admin
from .models import SystemLog

# Register your models here.
@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'admin', 'target_report_id', 'ip_address', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('action',)