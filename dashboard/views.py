from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from rest_framework import generics
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

from reports.models import Report
from .models import SystemLog
from .serializers import SystemLogSerializer


@extend_schema(
    tags=["Dashboard"],
    summary="List System Logs",
    description="Returns all system logs. Only administrators can access this endpoint.",
    responses={200: SystemLogSerializer(many=True)},
)
class SystemLogListView(generics.ListAPIView):
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    permission_classes = [IsAdminUser]


@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard Overview",
    description="Returns dashboard statistics including report counts and weekly report trends.",
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="DashboardOverviewResponse",
                fields={
                    "total_reports": serializers.IntegerField(),
                    "pending_reports": serializers.IntegerField(),
                    "verified_reports": serializers.IntegerField(),
                    "verification_rate": serializers.FloatField(),
                    "reports_this_week": serializers.ListField(
                        child=inline_serializer(
                            name="WeeklyReport",
                            fields={
                                "day": serializers.CharField(),
                                "count": serializers.IntegerField(),
                            },
                        )
                    ),
                },
            ),
            description="""
Example Response

```json
{
  "total_reports": 142,
  "pending_reports": 36,
  "verified_reports": 94,
  "verification_rate": 66.2,
  "reports_this_week": [
    {"day":"MON","count":8},
    {"day":"TUE","count":14},
    {"day":"WED","count":17},
    {"day":"THU","count":12},
    {"day":"FRI","count":20},
    {"day":"SAT","count":11},
    {"day":"SUN","count":7}
  ]
}
"""
)
},
)
class DashboardOverviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_reports = Report.objects.count()
        pending_reports = Report.objects.filter(
            status=Report.STATUS_PENDING
        ).count()
        verified_reports = Report.objects.filter(
            status=Report.STATUS_VERIFIED
        ).count()

        verification_rate = (
            round((verified_reports / total_reports) * 100, 1)
            if total_reports
            else 0
        )

        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())

        weekly_counts = []
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            count = Report.objects.filter(created_at__date=day).count()

            weekly_counts.append(
                {
                    "day": day.strftime("%a").upper(),
                    "count": count,
                }
            )

        return Response(
            {
                "total_reports": total_reports,
                "pending_reports": pending_reports,
                "verified_reports": verified_reports,
                "verification_rate": verification_rate,
                "reports_this_week": weekly_counts,
            }
        )


@extend_schema(
    tags=["Analytics"],
    summary="Crime Analytics",
    description="Returns crime hotspots and crime type distribution.",
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="CrimeAnalyticsResponse",
                fields={
                    "top_hotspot_zones": serializers.ListField(
                        child=inline_serializer(
                            name="Hotspot",
                            fields={
                                "address": serializers.CharField(),
                                "report_count": serializers.IntegerField(),
                            },
                        )
                    ),
                    "crime_type_breakdown": serializers.ListField(
                        child=inline_serializer(
                            name="CrimeTypeBreakdown",
                            fields={
                                "crime_type": serializers.CharField(),
                                "count": serializers.IntegerField(),
                            },
                        )
                    ),
                },
            ),
            description="""
Example Response

```json
{
  "top_hotspot_zones": [
    {
      "address": "Afe Babalola University Main Gate",
      "report_count": 15
    },
    {
      "address": "Fajuyi Park",
      "report_count": 12
    }
  ],
  "crime_type_breakdown": [
    {
      "crime_type": "Theft",
      "count": 61
    },
    {
      "crime_type": "Assault",
      "count": 32
    },
    {
      "crime_type": "Robbery",
      "count": 18
    }
  ]
}

"""
)
},
)
class CrimeAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        hotspots = (
            Report.objects.values("address")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        crime_type_breakdown = (
            Report.objects.values("crime_type__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response(
            {
                "top_hotspot_zones": [
                    {
                        "address": h["address"],
                        "report_count": h["count"],
                    }
                    for h in hotspots
                ],
                "crime_type_breakdown": [
                    {
                        "crime_type": c["crime_type__name"],
                        "count": c["count"],
                    }
                    for c in crime_type_breakdown
                ],
            }
        )
