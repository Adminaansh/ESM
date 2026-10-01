from rest_framework.views import APIView
from rest_framework.response import Response
from .services import ExecutionHubService

# --- LIFECYCLE CONTROLLERS ---
class RunJobView(APIView):
    def post(self, request):
        job = ExecutionHubService.run_job(request.data.get('chain_id'))
        return Response({"id": job.id, "status": "started"})

class KillJobView(APIView):
    def delete(self, request, id):
        ExecutionHubService.kill_job(id)
        return Response({"status": "killed"})

class PauseJobView(APIView):
    def patch(self, request):
        ExecutionHubService.pause_job(request.data.get('execution_id'))
        return Response({"status": "paused"})

class ResumeJobView(APIView):
    def patch(self, request):
        ExecutionHubService.resume_job(request.data.get('execution_id'))
        return Response({"status": "resumed"})

class ForceOKView(APIView):
    def post(self, request):
        ExecutionHubService.force_ok(request.data.get('execution_id'))
        return Response({"status": "force_completed"})

# --- BULK OPERATIONS ---
class BulkKillView(APIView):
    def post(self, request):
        for eid in request.data.get('execution_ids', []):
            ExecutionHubService.kill_job(eid)
        return Response({"status": "bulk_killed"})

class BulkPauseView(APIView):
    def post(self, request):
        for eid in request.data.get('execution_ids', []):
            ExecutionHubService.pause_job(eid)
        return Response({"status": "bulk_paused"})

# --- METADATA & CONFIG ---
class SetPriorityView(APIView):
    def patch(self, request, id):
        # Update priority logic
        return Response({"status": "priority_updated"})

class GetTopologyView(APIView):
    def get(self, request, id):
        # Return DAG structure
        return Response({"topology": "..."})

# ... (Continue adding classes for the remaining 10 endpoints)