# apps/infrastructure/urls.py
from django.urls import path
from .views import SystemHandshakeAPI, TelemetryIngestionAPI, OperationalOverviewAPI, AutomatedNodeDrainAPI

urlpatterns = [
    path('agent/handshake/', SystemHandshakeAPI.as_view(), name='infra-handshake'),
    path('telemetry/heartbeat/', TelemetryIngestionAPI.as_view(), name='infra-telemetry'),
    path('dashboard/overview/', OperationalOverviewAPI.as_view(), name='infra-dashboard'),
    path('nodes/auto-drain/', AutomatedNodeDrainAPI.as_view(), name='infra-drain'),
]