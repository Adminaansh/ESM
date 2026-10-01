# monitoring/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone

# Direct absolute imports from your flat root-level apps
from monitoring.models import WorkflowExecution, LiveExecutionLog, WorkflowExecutionHistory, ExternalAPITracking
from engine.models import Chain
from engine.execution_manager import execution_manager
from execution_hub.services import ExecutionHubService
from .models import *
import logging

logger = logging.getLogger(__name__)

class LiveExecutionControlView(APIView):
    """
    AppWorx/Control-M Style Control Hub.
    Handles dynamic live filtering (GET) and runtime operational signals (POST).
    """
    
    def get(self, request):
        """
        Queries and filters active running job streams.
        Supports parameters: ?state=RUNNING&search=CRON
        """
        state_filter = request.query_params.get('state', 'ALL')
        search_filter = request.query_params.get('search', None)
        
        # Read directly from parent process tracking model
        queryset = WorkflowExecution.objects.all().order_by("-started_at")

        if state_filter and state_filter != 'ALL':
            if state_filter == 'RUNNING_FAILED':
                queryset = queryset.filter(status__in=['RUNNING', 'FAILED'])
            else:
                queryset = queryset.filter(status=state_filter)
            
        # Apply filter on ID or invocation string
        if search_filter:
            queryset = queryset.filter(triggered_by__icontains=search_filter) | queryset.filter(id__icontains=search_filter)

        # Cap output at 250 rows to protect latency across 150+ jobs
        data_list = []
        for exe in queryset[:250]:
            chain_name = None
            try:
                chain = Chain.objects.filter(chain_code=int(exe.chain_id)).first() if str(exe.chain_id).isdigit() else None
                chain_name = chain.name if chain else None
            except Exception:
                chain_name = None

            started_at = exe.started_at
            ended_at = exe.ended_at
            elapsed = timezone.now() - started_at if not ended_at else ended_at - started_at
            elapsed_minutes = round(elapsed.total_seconds() / 60, 1)
            steps = []
            for step in exe.steps.all():
                steps.append({
                    'node_id': str(step.node_id) if step.node_id else None,
                    'job_name': step.job_name,
                    'status': step.status,
                    'sequence_index': step.sequence_index,
                    'started_at': step.started_at.isoformat() if step.started_at else None,
                    'ended_at': step.ended_at.isoformat() if step.ended_at else None,
                    'elapsed_minutes': step.elapsed_minutes,
                })

            data_list.append({
                "process_no": exe.process_no,
                "execution_id": str(exe.id),
                "chain_id": str(exe.chain_id),
                "chain_name": chain_name,
                "task_name": chain_name or exe.triggered_by,
                "source": exe.triggered_by,
                "state": exe.status,
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat() if ended_at else None,
                "elapsed_minutes": elapsed_minutes,
                "steps": steps
            })
            
        return Response({"executions": data_list}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Dispatches manual overrides directly down to your engine worker thread layer.
        """
        execution_id = request.data.get("execution_id")
        action = request.data.get("action")  # Expected: HOLD, RESUME, TERMINATE, FORCE_OK
        
        if not execution_id or not action:
            return Response(
                {"error": "Missing execution_id or action parameters"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Dispatch actions through the execution hub service.
            if action == "HOLD":
                job = ExecutionHubService.pause_job(execution_id)
            elif action == "RESUME":
                job = ExecutionHubService.resume_job(execution_id)
            elif action == "TERMINATE":
                job = ExecutionHubService.kill_job(execution_id)
            elif action == "FORCE_OK":
                job = ExecutionHubService.force_ok(execution_id)
            else:
                return Response(
                    {"error": f"Unsupported action protocol: {action}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                "status": "SUCCESS",
                "execution_id": str(job.id),
                "new_state": job.status,
                "message": f"Engine execution intercept [{action}] processed successfully."
            }, status=status.HTTP_200_OK)
            
        except WorkflowExecution.DoesNotExist:
            return Response(
                {"error": "Target execution reference block not found in database"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class InitiateExecutionAPI(APIView):
    """
    AUTOMATED STATE INITIATION
    Endpoint: POST /api/monitoring/execution/start/
    Fired by the core engine or scheduler to instantly allocate a running process row.
    """
    def post(self, request):
        chain_id = request.data.get("chain_id")
        trigger_source = request.data.get("source", "API_TRIGGER")

        if not chain_id:
            return Response({"error": "Missing target chain_id pattern"}, status=status.HTTP_400_BAD_REQUEST)

        run = ExecutionHubService.run_job(chain_id, source=trigger_source)

        return Response({
            "status": "tracking_active",
            "process_no": run.process_no,
            "execution_id": str(run.id),
            "chain_id": int(run.chain_id) if str(run.chain_id).isdigit() else run.chain_id,
            "state": run.status,
            "allocated_at": run.started_at.isoformat()
        }, status=status.HTTP_201_CREATED)


class LiveExecutionListView(APIView):
    """
    Returns all active pipeline executions for the enterprise grid.
    Completed/archived jobs are found in the history endpoint.
    """
    def get(self, request):
        # Return active plus recent completed/failed executions so they remain visible
        executions = WorkflowExecution.objects.filter(
            status__in=['QUEUED', 'RUNNING', 'PAUSED', 'HOLD',  'FAILED']
        ).order_by("-started_at")[:200] 
        data_list = []
        for exe in executions:
            chain_name = None
            try:
                chain = Chain.objects.filter(chain_code=int(exe.chain_id)).first() if str(exe.chain_id).isdigit() else None
                chain_name = chain.name if chain else None
            except Exception:
                chain_name = None

            steps = []
            for step in exe.steps.all():
                steps.append({
                    'node_id': str(step.node_id) if step.node_id else None,
                    'job_name': step.job_name,
                    'status': step.status,
                    'sequence_index': step.sequence_index,
                    'started_at': step.started_at.isoformat() if step.started_at else None,
                    'ended_at': step.ended_at.isoformat() if step.ended_at else None,
                    'elapsed_minutes': step.elapsed_minutes,
                })

            data_list.append({
                "process_no": exe.process_no,
                "execution_id": str(exe.id),
                "chain_id": str(exe.chain_id),
                "chain_name": chain_name,
                "task_name": chain_name or exe.triggered_by,
                "source": exe.triggered_by,
                "state": exe.status,
                "steps": steps
            })
        return Response({"executions": data_list}, status=status.HTTP_200_OK)


class LiveExecutionHistoryView(APIView):
    """
    Returns archived execution history for completed and terminated runs.
    """
    def get(self, request):
        try:
            requested_limit = int(request.query_params.get('limit', 50))
        except (TypeError, ValueError):
            requested_limit = 50

        limit = min(max(requested_limit, 1), 50)
        executions = WorkflowExecutionHistory.objects.all().order_by('-archived_at')[:limit]
        data_list = []
        for exe in executions:
            data_list.append({
                "process_no": exe.process_no,
                "execution_id": str(exe.original_execution_id or exe.id),
                "chain_id": exe.chain_id,
                "chain_name": exe.chain_name,
                "task_name": exe.task_name,
                "source": exe.source,
                "state": exe.status,
                "started_at": exe.started_at.isoformat(),
                "ended_at": exe.ended_at.isoformat() if exe.ended_at else None,
                "archived_at": exe.archived_at.isoformat(),
                "has_output": bool(exe.compiled_console_output),
            })
        return Response({"executions": data_list}, status=status.HTTP_200_OK)


class HistoryExecutionOutputAPI(APIView):
    """
    Return archived console output for a completed historical execution.
    """
    def get(self, request, process_no):
        try:
            history = WorkflowExecutionHistory.objects.get(process_no=process_no)
        except WorkflowExecutionHistory.DoesNotExist:
            return Response({"error": "History record not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "process_no": history.process_no,
            "chain_id": history.chain_id,
            "task_name": history.task_name,
            "state": history.status,
            "output": history.compiled_console_output or 'No archived output was captured for this run.',
        }, status=status.HTTP_200_OK)


class IngestTelemetryLogsAPI(APIView):
    """
    HIGH-FREQUENCY APPEND-ONLY LOG INGESTION
    Endpoint: POST /api/monitoring/execution/log/
    Called by orchestration runners to append streaming stdout/stderr data frames to the process database.
    """
    def post(self, request):
        execution_id = request.data.get("execution_id")
        node_id = request.data.get("node_id")
        level = request.data.get("level", "INFO")
        log_payload = request.data.get("message")

        if not execution_id or not log_payload:
            return Response({"error": "Incomplete tracking parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
        except (WorkflowExecution.DoesNotExist, ValueError):
            return Response({"error": "Execution tracking record not found"}, status=status.HTTP_404_NOT_FOUND)

        # Perform atomic append operation
        log_entry = LiveExecutionLog.objects.create(
            execution=execution,
            node_id=node_id,
            log_level=level,
            message=log_payload
        )

        return Response({
            "status": "log_appended",
            "log_id": str(log_entry.id)
        }, status=status.HTTP_202_ACCEPTED)


class GlobalLiveConsoleAPI(APIView):
    """
    REAL-TIME VISIBILITY OVERRIDE
    Endpoint: GET /api/monitoring/process/{process_no}/stream/
    Flattens the entire runtime state profile and returns a compiled console log history to the UI.
    """
    def get(self, request, process_no):
        try:
            execution = WorkflowExecution.objects.prefetch_related('logs').get(process_no=process_no)
        except WorkflowExecution.DoesNotExist:
            return Response({"error": "Process sequence track index not found"}, status=status.HTTP_404_NOT_FOUND)

        extracted_logs = [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.log_level,
                "node_id": str(log.node_id) if log.node_id else None,
                "output": log.message
            }
            for log in execution.logs.all()
        ]

        return Response({
            "process_metadata": {
                "process_no": execution.process_no,
                "execution_id": str(execution.id),
                "blueprint_chain_id": str(execution.chain_id),
                "execution_state": execution.status,
                "uptime_start": execution.started_at.isoformat(),
                "uptime_end": execution.ended_at.isoformat() if execution.ended_at else None,
            },
            "console_streams": extracted_logs
        }, status=status.HTTP_200_OK)


class DeleteExecutionAPI(APIView):
    """
    Forcefully delete/archive an execution from live monitoring.
    Moves it to history and terminates if still running.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, execution_id):
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            process_no = execution.process_no

            logger.info(f"Force deleting execution {execution_id} (process #{process_no})")

            # Terminate if still running
            if execution.status in ('RUNNING', 'QUEUED', 'PAUSED', 'HOLD'):
                execution.status = 'TERMINATED'
                execution.ended_at = timezone.now()
                execution.save()

            # Archive to history
            ExecutionHubService._archive_execution(execution)

            # Delete from live execution table
            execution.delete()

            logger.info(f"Execution {execution_id} (process #{process_no}) successfully deleted and archived")

            return Response({
                "status": "success",
                "message": f"Execution #{process_no} deleted and archived",
                "process_no": process_no
            }, status=status.HTTP_200_OK)

        except WorkflowExecution.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Execution not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.exception(f"Error deleting execution {execution_id}: {exc}")
            return Response({
                "status": "error",
                "message": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalAPIStatusCallbackAPI(APIView):
    """
    Endpoint for external systems to report async API completion status.
    """
    permission_classes = []

    def post(self, request):
        external_job_id = request.data.get('external_job_id')
        tracking_id = request.data.get('tracking_id')
        status_value = request.data.get('status')
        message = request.data.get('message', '')
        callback_secret = request.data.get('callback_secret', '')

        if not status_value or status_value not in ['COMPLETED', 'FAILED']:
            return Response({
                'status': 'error',
                'message': 'status must be COMPLETED or FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)

        tracking = None
        if tracking_id:
            try:
                tracking = ExternalAPITracking.objects.get(id=tracking_id)
            except ExternalAPITracking.DoesNotExist:
                tracking = None

        if not tracking and external_job_id:
            tracking = ExternalAPITracking.objects.filter(external_job_id=external_job_id).first()

        if not tracking:
            return Response({
                'status': 'error',
                'message': 'Tracking record not found for provided identifiers'
            }, status=status.HTTP_404_NOT_FOUND)

        if tracking.callback_secret and callback_secret != tracking.callback_secret:
            return Response({
                'status': 'error',
                'message': 'Invalid callback secret'
            }, status=status.HTTP_403_FORBIDDEN)

        tracking.status = status_value
        tracking.response_summary = message or tracking.response_summary
        tracking.save()

        step = tracking.step
        step.ended_at = timezone.now()
        step.status = 'COMPLETED' if status_value == 'COMPLETED' else 'FAILED'
        step.save()

        execution = step.execution
        if status_value == 'FAILED':
            execution.status = 'FAILED'
            execution.ended_at = timezone.now()
            execution.save()

        LiveExecutionLog.objects.create(
            execution=execution,
            node_id=step.node_id,
            log_level='INFO' if status_value == 'COMPLETED' else 'ERROR',
            message=f'[EXTERNAL_API_CALLBACK] external_job_id={tracking.external_job_id or tracking.id} status={status_value} message={message}'
        )

        return Response({
            'status': 'success',
            'tracking_id': str(tracking.id),
            'execution_status': execution.status,
            'step_status': step.status
        }, status=status.HTTP_200_OK)