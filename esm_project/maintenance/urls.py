# apps/maintenance/urls.py
from django.urls import path
from .views import AutomatedDatabasePurgeAPI, EngineSystemHealthAPI

urlpatterns = [
    path('database/purge/', AutomatedDatabasePurgeAPI.as_view(), name='maintenance-purge'),
    path('system/health/', EngineSystemHealthAPI.as_view(), name='maintenance-health'),
]