# apps/scheduler/views.py
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import AutomatedSchedule, TriggerIncidentLog
from .serializers import AutomatedScheduleSerializer, TriggerIncidentLogSerializer
from .tasks import evaluate_schedules
from rest_framework import viewsets
from execution_hub.services import ExecutionHubService


class SystemEvaluationPulseAPI(APIView):
    """
    AUTOMATED TRIGGER EVALUATION SYSTEM
    Endpoint: POST /api/scheduler/engine/evaluate/
    Hit by a system daemon or lightweight background service to check 
    which chains are due for execution based on current timestamps.
    """
    def post(self, request):
        result = evaluate_schedules()
        return Response(result, status=status.HTTP_200_OK)


class ToggleScheduleStateAPI(APIView):
    """
    AUTOMATED SCHEDULER CIRCUIT BREAKER
    Endpoint: PATCH /api/scheduler/rule/toggle/
    Allows error-handling logic or health watchdogs to immediately kill or resume a script loop.
    """
    def patch(self, request):
        schedule_id = request.data.get("schedule_id")
        set_active = request.data.get("enabled") # True or False

        if schedule_id is None or set_active is None:
            return Response({"error": "Incomplete configuration state fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rule = AutomatedSchedule.objects.get(id=schedule_id)
        except (AutomatedSchedule.DoesNotExist, ValueError):
            return Response({"error": "Target automation schedule profile not found"}, status=status.HTTP_404_NOT_FOUND)

        rule.is_enabled = bool(set_active)
        # Clear calculation targets if disabled to reset validation targets
        if not rule.is_enabled:
            rule.next_expected_fire = None
        rule.save()

        return Response({
            "schedule_name": rule.name,
            "is_enabled": rule.is_enabled,
            "system_action": "AUTOMATED_LOOP_MUTED" if not rule.is_enabled else "AUTOMATED_LOOP_ACTIVE"
        }, status=status.HTTP_200_OK)


class AutomatedScheduleViewSet(viewsets.ModelViewSet):
    """CRUD API for managing scheduled chain trigger rules."""
    queryset = AutomatedSchedule.objects.all().order_by('-created_at')
    serializer_class = AutomatedScheduleSerializer

    def perform_destroy(self, instance):
        # Optionally record a final incident or cleanup before deletion
        instance.delete()