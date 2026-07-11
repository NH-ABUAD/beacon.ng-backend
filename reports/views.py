from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import ReportFilter
from .models import CrimeType, Evidence, Report, ReportTimeline
from .permissions import IsAdminOrOwnerOrReadOnly, IsAdminUser
from .serializers import (
    CrimeTypeSerializer,
    EvidenceSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    ReportTimelineSerializer,
)
from .services import ReportService


class CrimeTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = CrimeType.objects.filter(is_active=True)
    serializer_class = CrimeTypeSerializer
    permission_classes = [AllowAny]


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        report = ReportService.create_report(serializer.validated_data, requester=request.user if request.user.is_authenticated else None)
        response_serializer = ReportSerializer(report)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('Only administrators can update reports.')

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('Only administrators can delete reports.')
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        reports = self.queryset.order_by('-created_at')[:10]
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my')
    def my_reports(self, request):
        reports = self.get_queryset().filter(reporter=request.user)
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

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

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser], url_path='evidence')
    def evidence(self, request, pk=None):
        report = self.get_object()
        serializer = EvidenceSerializer(data=request.data, context={'report': report})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        report = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')
        if new_status not in dict(Report.STATUS_CHOICES):
            return Response({'status': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        ReportService.update_status(report, new_status, updated_by=request.user if request.user.is_authenticated else None, note=note)
        return Response({'status': new_status})

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        report = self.get_object()
        ReportService.update_status(report, Report.STATUS_VERIFIED, updated_by=request.user if request.user.is_authenticated else None, note='Verified by admin.')
        return Response({'status': Report.STATUS_VERIFIED})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        report = self.get_object()
        ReportService.update_status(report, Report.STATUS_REJECTED, updated_by=request.user if request.user.is_authenticated else None, note='Rejected by admin.')
        return Response({'status': Report.STATUS_REJECTED})


class EvidenceViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Evidence.objects.select_related('report')
    serializer_class = EvidenceSerializer
    permission_classes = [IsAdminOrOwnerOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
