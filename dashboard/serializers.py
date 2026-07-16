from rest_framework import serializers
from .models import SystemLog


class SystemLogSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source='admin.email', read_only=True)

    class Meta:
        model = SystemLog
        fields = ['id', 'admin_email', 'action', 'target_report_id', 'ip_address', 'created_at']