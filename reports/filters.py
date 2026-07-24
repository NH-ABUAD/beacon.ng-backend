import django_filters

from .models import Report


class ReportFilter(django_filters.FilterSet):
    crime_type = django_filters.CharFilter(
        field_name='crime_type__name',
        lookup_expr='icontains',
        help_text="Filter by crime type name, partial match allowed (e.g. 'theft' matches 'Theft').",
    )
    status = django_filters.CharFilter(
        field_name='status',
        lookup_expr='icontains',
        help_text="Filter by report status: Pending, Verified, Rejected, Under Investigation, Resolved, Closed.",
    )
    priority = django_filters.CharFilter(
        field_name='priority',
        lookup_expr='icontains',
        help_text="Filter by priority level: Low, Medium, High, Critical.",
    )
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Return reports created on or after this datetime (ISO 8601, e.g. 2026-07-01T00:00:00Z).",
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Return reports created on or before this datetime (ISO 8601, e.g. 2026-07-31T23:59:59Z).",
    )

    class Meta:
        model = Report
        fields = ['crime_type', 'status', 'priority', 'anonymous', 'created_after', 'created_before']