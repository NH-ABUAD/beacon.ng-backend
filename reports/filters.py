import django_filters

from .models import Report


class ReportFilter(django_filters.FilterSet):
    crime_type = django_filters.CharFilter(field_name='crime_type__name', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    priority = django_filters.CharFilter(field_name='priority', lookup_expr='icontains')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Report
        fields = ['crime_type', 'status', 'priority', 'anonymous', 'created_after', 'created_before']
