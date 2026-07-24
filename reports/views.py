from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import ReportFilter
from .models import CrimeType, Evidence, Report, ReportTimeline, Notification
from .permissions import IsAdminOrOwnerOrReadOnly, IsAdminUser
from .serializers import (
    CrimeTypeSerializer,
    EvidenceSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    ReportTimelineSerializer,
    NotificationSerializer
)
from .services import ReportService


@extend_schema(tags=["Reports"])
class CrimeTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    List all active crime types. Read-only — crime types are seeded via
    a management command, not created through the API.
    """
    queryset = CrimeType.objects.filter(is_active=True)
    serializer_class = CrimeTypeSerializer
    permission_classes = [AllowAny]


@extend_schema(tags=["Reports"])
class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('crime_type', 'reporter').prefetch_related('evidence', 'timeline')
    serializer_class = ReportSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReportFilter
    search_fields = ['tracking_code', 'address', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in {'create', 'list', 'recent', 'crime_map', 'track'}:
            return [AllowAny()]
        if self.action in {'my_reports'}:
            return [IsAuthenticated()]
        if self.action in {'update', 'partial_update', 'destroy', 'verify', 'reject', 'update_status'}:
            return [IsAdminUser()]
        return [IsAdminOrOwnerOrReadOnly()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'my_reports':
            return qs.filter(reporter=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportSerializer

    @extend_schema(
        summary="Submit a crime report",
        description=(
            "Creates a new crime report. `crime_type` is passed by name (e.g. `\"Robbery\"`), "
            "not ID. Set `anonymous: true` to submit without attaching your identity — the "
            "`reporter` field is left null on the report even if you're logged in. Open to "
            "both authenticated and unauthenticated users."
        ),
        request=ReportCreateSerializer,
        examples=[
            OpenApiExample(
                "Report submission",
                value={
                    "crime_type": "Robbery",
                    "description": "Two men on a motorcycle attempted to snatch a bag near the bus stop",
                    "incident_datetime": "2026-07-12T14:32:00Z",
                    "address": "Yaba, Lagos",
                    "latitude": "6.5244",
                    "longitude": "3.3792",
                    "anonymous": False,
                },
                request_only=True,
            )
        ],
        responses={201: ReportSerializer, 400: OpenApiResponse(description="Validation error")},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        report = ReportService.create_report(serializer.validated_data, requester=request.user if request.user.is_authenticated else None)
        response_serializer = ReportSerializer(report)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="List reports",
        description=(
            "Returns all reports. Supports filtering via query params (status, crime_type, "
            "priority, anonymous, created_after/created_before), search (tracking_code, "
            "address, description), and ordering."
        ),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Retrieve a report")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a report (Admin)",
        description="Full or partial update of a report. Admin-only.",
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('Only administrators can update reports.')

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Delete a report (Admin)",
        description="Permanently deletes a report. Admin-only.",
        responses={204: OpenApiResponse(description="Report deleted.")},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('Only administrators can delete reports.')
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Recent reports",
        description="Returns the 10 most recently created reports, newest first.",
        responses={200: ReportSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        reports = self.queryset.order_by('-created_at')[:10]
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="My reports",
        description="Returns only the authenticated user's own submitted reports. Requires login.",
        responses={200: ReportSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='my')
    def my_reports(self, request):
        reports = self.get_queryset().filter(reporter=request.user)
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Track a report by tracking code",
        description=(
            "Public lookup of a report's status and full timeline using its tracking code "
            "(e.g. `BCR-RJKWXO`), rather than its internal ID. No authentication required."
        ),
        responses={200: OpenApiResponse(description="Tracking code, status, and timeline entries.")},
    )
    @action(detail=False, methods=['get'], url_path='track/(?P<tracking_code>[^/.]+)')
    def track(self, request, tracking_code=None):
        report = get_object_or_404(Report, tracking_code=tracking_code)
        timeline = ReportTimeline.objects.filter(report=report)
        payload = {
            'tracking_code': report.tracking_code,
            'status': report.status,
            'timeline': ReportTimelineSerializer(timeline, many=True).data,
            'created_at': report.created_at,
            'updated_at': report.updated_at,
        }
        return Response(payload)

    @extend_schema(
        summary="Crime map data",
        description=(
            "Returns latitude, longitude, crime type, priority, and status for up to 100 "
            "reports with a set location — feeds the interactive crime map."
        ),
        responses={200: OpenApiResponse(description="List of {latitude, longitude, crime_type, priority, status}.")},
    )
    @action(detail=False, methods=['get'], url_path='crime-map')
    def crime_map(self, request):
        reports = self.queryset.filter(latitude__isnull=False, longitude__isnull=False)[:100]
        data = [
            {
                'latitude': float(report.latitude),
                'longitude': float(report.longitude),
                'crime_type': report.crime_type.name,
                'priority': report.priority,
                'status': report.status,
            }
            for report in reports
        ]
        return Response(data)

    @extend_schema(
        summary="Upload evidence",
        description=(
            "Attach an image or video to a specific report. Accepts multipart/form-data. "
            "Restricted to the report's owner or an admin."
        ),
        request={'multipart/form-data': EvidenceSerializer},
        responses={201: EvidenceSerializer},
    )
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser], url_path='evidence')
    def evidence(self, request, pk=None):
        report = self.get_object()
        serializer = EvidenceSerializer(data=request.data, context={'report': report})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Update report status (Admin)",
        description="Manually set a report's status, with an optional note. Admin-only.",
        request=OpenApiExample("Status update", value={"status": "Under Investigation", "note": "Assigned to field officer."}, request_only=True),
        responses={200: OpenApiResponse(description="Updated status."), 400: OpenApiResponse(description="Invalid status.")},
    )
    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        report = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')
        if new_status not in dict(Report.STATUS_CHOICES):
            return Response({'status': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        ReportService.update_status(report, new_status, updated_by=request.user if request.user.is_authenticated else None, note=note)
        return Response({'status': new_status})

    @extend_schema(
        summary="Verify a report (Admin)",
        description="Marks a report as Verified. Logged to the system audit trail. Admin-only.",
        request=None,
        responses={200: OpenApiResponse(description='{"status": "Verified"}')},
    )
    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        report = self.get_object()
        ReportService.update_status(report, Report.STATUS_VERIFIED, updated_by=request.user if request.user.is_authenticated else None, note='Verified by admin.')
        return Response({'status': Report.STATUS_VERIFIED})

    @extend_schema(
        summary="Reject a report (Admin)",
        description="Marks a report as Rejected. Logged to the system audit trail. Admin-only.",
        request=None,
        responses={200: OpenApiResponse(description='{"status": "Rejected"}')},
    )
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        report = self.get_object()
        ReportService.update_status(report, Report.STATUS_REJECTED, updated_by=request.user if request.user.is_authenticated else None, note='Rejected by admin.')
        return Response({'status': Report.STATUS_REJECTED})


@extend_schema(tags=["Reports"])
class EvidenceViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Evidence.objects.select_related('report')
    serializer_class = EvidenceSerializer
    permission_classes = [IsAdminOrOwnerOrReadOnly]

    @extend_schema(
        summary="Delete evidence",
        description="Deletes a piece of evidence. Restricted to the report's owner or an admin.",
        responses={204: OpenApiResponse(description="Evidence deleted.")},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Notifications"])
class NotificationViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    List or update the authenticated user's own notifications.
    Always scoped to the current user — you cannot see or edit anyone else's.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)