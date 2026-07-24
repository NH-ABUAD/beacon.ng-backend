from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CrimeTypeViewSet, EvidenceViewSet, ReportViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'crime-types', CrimeTypeViewSet, basename='crime-type')
router.register(r'evidence', EvidenceViewSet, basename='evidence')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]