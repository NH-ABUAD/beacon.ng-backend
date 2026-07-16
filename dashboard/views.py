from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from .models import SystemLog
from .serializers import SystemLogSerializer
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from reports.models import Report


class SystemLogListView(generics.ListAPIView):
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    permission_classes = [IsAdminUser]
    
    
class DashboardOverviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_reports = Report.objects.count()
        pending_reports = Report.objects.filter(status=Report.STATUS_PENDING).count()
        verified_reports = Report.objects.filter(status=Report.STATUS_VERIFIED).count()

        verification_rate = round((verified_reports / total_reports) * 100, 1) if total_reports else 0

        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())  # Monday

        weekly_counts = []
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            count = Report.objects.filter(created_at__date=day).count()
            weekly_counts.append({
                'day': day.strftime('%a').upper(),
                'count': count,
            })

        return Response({
            'total_reports': total_reports,
            'pending_reports': pending_reports,
            'verified_reports': verified_reports,
            'verification_rate': verification_rate,
            'reports_this_week': weekly_counts,
        })
        
class CrimeAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        hotspots = (
            Report.objects.values('address')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        crime_type_breakdown = (
            Report.objects.values('crime_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response({
            'top_hotspot_zones': [
                {'address': h['address'], 'report_count': h['count']} for h in hotspots
            ],
            'crime_type_breakdown': [
                {'crime_type': c['crime_type__name'], 'count': c['count']} for c in crime_type_breakdown
            ],
        })