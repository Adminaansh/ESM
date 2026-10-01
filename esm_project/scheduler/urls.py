# apps/scheduler/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SystemEvaluationPulseAPI, ToggleScheduleStateAPI, AutomatedScheduleViewSet

router = DefaultRouter()
router.register(r'schedules', AutomatedScheduleViewSet, basename='schedules')

urlpatterns = [
    path('', include(router.urls)),
    path('engine/evaluate/', SystemEvaluationPulseAPI.as_view(), name='schedule-evaluate'),
    path('rule/toggle/', ToggleScheduleStateAPI.as_view(), name='schedule-toggle'),
]