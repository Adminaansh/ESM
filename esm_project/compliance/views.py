# apps/compliance/views.py
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import HistoricalExecutionArchive, SecurityAuditEvent

class AutomatedLogArchivalSweepAPI(APIView):
    """
    AUTOMATED ARCHIVAL ENGINE
    Endpoint: POST /api/compliance/archive/sweep/
    """
    def post(self, request):
        try:
            execution_id = request.data.get("execution_id")
            process_no = request.data.get("process_no")
            chain_id = request.data.get("chain_id")
            status_flag = request.data.get("status", "UNKNOWN")
            caller = request.data.get("triggered_by", "SYSTEM")
            duration = float(request.data.get("duration_seconds", 0.0))
            raw_logs_list = request.data.get("logs_array", [])

            if not execution_id or not process_no:
                return Response({"error": "Missing fundamental tracking criteria"}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure incoming values are explicitly cast to valid UUID types 
            clean_exec_id = uuid.UUID(str(execution_id))
            clean_chain_id = str(chain_id) if chain_id else ''

            # Flatten log fragments array into a single text document string
            compiled_dump = "\n".join(raw_logs_list) if isinstance(raw_logs_list, list) else str(raw_logs_list)

            # Write safely into historic cold-storage using an update_or_create payload
            archive_entry, created = HistoricalExecutionArchive.objects.update_or_create(
                original_execution_id=clean_exec_id,
                defaults={
                    "process_no": int(process_no),
                    "chain_id": clean_chain_id,
                    "final_status": str(status_flag),
                    "triggered_by": str(caller),
                    "execution_duration_seconds": duration,
                    "compiled_console_output": compiled_dump
                }
            )

            return Response({
                "status": "archived_successfully",
                "archive_id": str(archive_entry.id),
                "process_no": archive_entry.process_no,
                "action": "created" if created else "overwritten",
                "bytes_processed": len(compiled_dump)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Shield the endpoint from throwing a raw HTML crash response
            return Response({
                "error": "Internal archival processing pipeline failure",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmitSecurityAuditEventAPI(APIView):
    """
    IMMUTABLE AUDIT INGESTION
    Endpoint: POST /api/compliance/audit/incident/
    Called internally by security loops, vault failures, or network watchdogs to index an incident flag.
    """
    def post(self, request):
        domain = request.data.get("subsystem")
        action = request.data.get("event")
        level = request.data.get("severity", "LOW")
        context = request.data.get("context_meta", {})

        if not domain or not action:
            return Response({"error": "Incomplete audit parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # Automatically record system incident trace anomalies
        incident = SecurityAuditEvent.objects.create(
            subsystem=domain.strip().upper(),
            event_type=action.strip().upper(),
            severity=level,
            metadata_json=context
        )

        # Automation Hook: In a live enterprise engine, if severity == 'HIGH', 
        # this code block would fire Slack/PagerDuty alerts instantly.

        return Response({
            "status": "incident_recorded",
            "incident_id": str(incident.id),
            "severity_assigned": incident.severity
        }, status=status.HTTP_201_CREATED)