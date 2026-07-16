from django.urls import path
from .views import SystemLogListView, DashboardOverviewView

urlpatterns = [
    path('logs/', SystemLogListView.as_view(), name='system-logs'),
    path('overview/', DashboardOverviewView.as_view(), name='dashboard-overview')
]