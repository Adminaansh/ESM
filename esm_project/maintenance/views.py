# apps/maintenance/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.apps import apps
from .models import MaintenancePolicy, CleanupExecutionLog

class AutomatedDatabasePurgeAPI(APIView):
    """
    AUTOMATED PURGE ENGINE
    Endpoint: POST /api/maintenance/database/purge/
    Triggered periodically by a system cron or automated watcher loop to enforce data retention policies.
    """
    def post(self, request):
        target_subsystem = request.data.get("subsystem") # LIVE_LOGS, HEARTBEATS, INCIDENTS
        now = timezone.now()
        
        try:
            policy = MaintenancePolicy.objects.get(subsystem=target_subsystem, is_active=True)
        except MaintenancePolicy.DoesNotExist:
            return Response({"error": f"No active cleanup policy found for target: {target_subsystem}"}, status=status.HTTP_404_NOT_FOUND)

        # Calculate the precise historical expiration threshold
        cutoff_date = now - timedelta(days=policy.retention_days)
        deleted_count = 0

        try:
            # Dynamically map policies to the actual database models we created earlier
            if target_subsystem == 'LIVE_LOGS':
                # Target: LiveExecutionLog from Module 5
                LogModel = apps.get_model('monitoring', 'LiveExecutionLog')
                # Bulk delete operations bypass slow row-by-row iterative checks
                deleted_count, _ = LogModel.objects.filter(timestamp__lt=cutoff_date).delete()
                
            elif target_subsystem == 'HEARTBEATS':
                # Target: InfrastructureTarget metrics data can be rolled back or wiped
                TargetModel = apps.get_model('infrastructure', 'InfrastructureTarget')
                # Reset stale metrics instead of deleting physical discovered infrastructure rows
                deleted_count = TargetModel.objects.filter(last_heartbeat__lt=cutoff_date).update(
                    cpu_utilization=0.0, 
                    memory_utilization=0.0,
                    status='OFFLINE'
                )

            elif target_subsystem == 'INCIDENTS':
                # Target: SecurityAuditEvent from Module 8
                AuditModel = apps.get_model('compliance', 'SecurityAuditEvent')
                deleted_count, _ = AuditModel.objects.filter(timestamp__lt=cutoff_date).delete()

            # Record a successful cleanup run tracking entry
            # Simulating data footprint shrink mapping (approx 0.01MB per row average)
            reclaimed_estimate = round(deleted_count * 0.01, 2)
            
            CleanupExecutionLog.objects.create(
                policy=policy,
                rows_deleted=deleted_count,
                space_reclaimed_mb=reclaimed_estimate,
                was_successful=True
            )

            return Response({
                "status": "purge_complete",
                "subsystem_cleaned": target_subsystem,
                "records_purged_count": deleted_count,
                "estimated_space_reclaimed_mb": reclaimed_estimate,
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Fallback error mapping logic to catch breaking structural shifts
            CleanupExecutionLog.objects.create(
                policy=policy,
                rows_deleted=0,
                was_successful=False,
                error_message=str(e)
            )
            return Response({"error": f"Internal database prune failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EngineSystemHealthAPI(APIView):
    """
    CRITICAL HEALTH WATCHDOG
    Endpoint: GET /api/maintenance/system/health/
    Invoked on-demand by operational orchestrators to perform a lightweight health validation sweep.
    """
    def get(self, request):
        # Dynamically inspect active targets from across your modular components
        TargetModel = apps.get_model('infrastructure', 'InfrastructureTarget')
        total_nodes = TargetModel.objects.count()
        unhealthy_nodes = TargetModel.objects.filter(status='UNHEALTHY').count()
        offline_nodes = TargetModel.objects.filter(status='OFFLINE').count()
        
        # Calculate systemic risk health metrics index ratio
        health_ratio = 100.0
        if total_nodes > 0:
            health_ratio = round(((total_nodes - (unhealthy_nodes + offline_nodes)) / total_nodes) * 100, 2)

        return Response({
            "system_health_metrics": {
                "overall_score_percent": health_ratio,
                "infrastructure_summary": {
                    "monitored_assets": total_nodes,
                    "degraded_performance": unhealthy_nodes,
                    "disconnected_nodes": offline_nodes
                },
                "engine_status": "OPERATIONAL" if health_ratio > 75.0 else "DEGRADED_CRITICAL",
                "evaluated_at": timezone.now().isoformat()
            }
        }, status=status.HTTP_200_OK)