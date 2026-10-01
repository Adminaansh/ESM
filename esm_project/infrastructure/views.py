# apps/infrastructure/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import InfrastructureTarget, RemoteAgentSession



class AgentNodeRegistryListView(APIView):
    """
    Returns the complete list of registered clusters and edge infrastructure nodes.
    """
    def get(self, request):
        nodes = InfrastructureTarget.objects.all()
        node_pool = []
        for node in nodes:
            node_pool.append({
                "hostname": node.hostname,
                "ip_address": node.ip_address,
                "target_type": node.target_type,
                "status": node.engine_status, # e.g., UNHEALTHY, HEALTHY, DEGRADED
                "cpu": getattr(node, 'last_cpu_reading', 0.0),
                "ram": getattr(node, 'last_memory_reading', 0.0)
            })
        return Response({"nodes": node_pool}, status=200)
    

    
class SystemHandshakeAPI(APIView):
    """
    AUTOMATED DISCOVERY ENGINE
    Endpoint: POST /api/infrastructure/agent/handshake/
    Fired dynamically by an edge agent daemon when it starts up on a remote server.
    """
    def post(self, request):
        hostname = request.data.get("hostname")
        ip_address = request.data.get("ip_address")
        agent_ver = request.data.get("agent_version", "1.0.0")
        node_type = request.data.get("target_type", "LINUX_SERVER")

        if not hostname or not ip_address:
            return Response({"error": "Invalid handshake payload"}, status=status.HTTP_400_BAD_REQUEST)

        # Upsert: Update parameters if it exists, or dynamically create an entry if new
        target, created = InfrastructureTarget.objects.update_or_create(
            host_address=ip_address,
            defaults={
                "name": hostname,
                "target_type": node_type,
                "status": "HEALTHY",
                "last_heartbeat": timezone.now()
            }
        )

        # Establish or automatically rotate the tracking token session
        session, _ = RemoteAgentSession.objects.update_or_create(
            target=target,
            defaults={"agent_version": agent_ver, "is_active": True}
        )

        return Response({
            "status": "connected",
            "node_id": str(target.id),
            "authorization_token": str(session.secure_token),
            "action_executed": "discovered_new_asset" if created else "refreshed_existing_asset"
        }, status=status.HTTP_200_OK)


class TelemetryIngestionAPI(APIView):
    """
    AUTOMATED HEALTH WATCHDOG
    Endpoint: POST /api/infrastructure/telemetry/heartbeat/
    Ingests vital metrics and evaluates status transitions without human oversight.
    """
    def post(self, request):
        auth_token = request.data.get("token")
        cpu = float(request.data.get("cpu_percent", 0.0))
        memory = float(request.data.get("memory_percent", 0.0))

        try:
            # Validate agent credentials directly in our application layer
            session = RemoteAgentSession.objects.select_related('target').get(secure_token=auth_token, is_active=True)
            target = session.target
        except (RemoteAgentSession.DoesNotExist, ValueError):
            return Response({"error": "Unauthorized / Stale Agent Token"}, status=status.HTTP_401_UNAUTHORIZED)

        # System Rules: Automated status transitions based on resource pressure
        if cpu > 90.0 or memory > 92.0:
            target.status = "UNHEALTHY"
        else:
            target.status = "HEALTHY"

        target.cpu_utilization = cpu
        target.memory_utilization = memory
        target.last_heartbeat = timezone.now()
        target.save()

        # Touch timestamp
        session.save()

        return Response({
            "node": target.name,
            "engine_status": target.status,
            "acknowledged_at": timezone.now().isoformat()
        }, status=status.HTTP_202_ACCEPTED)


class OperationalOverviewAPI(APIView):
    """
    REAL-TIME VISIBILITY MATRIX
    Endpoint: GET /api/infrastructure/dashboard/overview/
    Flattens resource metrics instantly for the main UI metrics engine.
    """
    def get(self, request):
        dataset = InfrastructureTarget.objects.all()
        
        return Response({
            "infrastructure_load_summary": {
                "total_monitored_nodes": dataset.count(),
                "healthy_nodes": dataset.filter(status="HEALTHY").count(),
                "high_pressure_nodes": dataset.filter(status="UNHEALTHY").count(),
                "disconnected_nodes": dataset.filter(status="OFFLINE").count(),
                "draining_nodes": dataset.filter(status="DRAINING").count()
            }
        }, status=status.HTTP_200_OK)


class AutomatedNodeDrainAPI(APIView):
    """
    AUTOMATED INFRASTRUCTURE ISOLATION
    Endpoint: POST /api/infrastructure/nodes/auto-drain/
    Fired by system health check workers to gracefully shift load away from malfunctioning targets.
    """
    def post(self, request):
        target_id = request.data.get("node_id")
        reason = request.data.get("reason", "AUTOMATED_HEALTH_TRIGGER")

        try:
            target = InfrastructureTarget.objects.get(id=target_id)
        except (InfrastructureTarget.DoesNotExist, ValueError):
            return Response({"error": "Monitored node not found"}, status=status.HTTP_404_NOT_FOUND)

        target.status = "DRAINING"
        target.save()

        # Deactivate session to trigger agent authentication recycling
        RemoteAgentSession.objects.filter(target=target).update(is_active=False)

        return Response({
            "node_name": target.name,
            "current_state": target.status,
            "action_executed": "NODE_ISOLATED",
            "incident_log": f"Node isolated automatically. Reason: {reason}"
        }, status=status.HTTP_200_OK)