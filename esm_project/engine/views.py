from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Chain, ChainNode
from .serializers import ChainSerializer
from studio.models import JobObject

class ChainViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Workflow Chains.
    Automatically handles the nested creation of Nodes and Edges.
    """
    # Order by newest created so you see your latest workflows first
    queryset = Chain.objects.all().order_by('-created_at')
    serializer_class = ChainSerializer

    def create(self, request, *args, **kwargs):
        """
        Custom create method to provide clear feedback during 
        API development and testing.
        """
        serializer = self.get_serializer(data=request.data)
        
        # raise_exception=True handles 400 Bad Request automatically
        serializer.is_valid(raise_exception=True)
        
        # This calls the .create() method we wrote in the Serializer
        self.perform_create(serializer)
        
        return Response(
            {
                "status": "success",
                "message": f"Workflow '{serializer.data['name']}' created successfully.",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        chain = self.get_object()
        job_ids = list(chain.nodes.values_list('job_id', flat=True))
        self.perform_destroy(chain)

        for job_id in set(job_ids):
            if not ChainNode.objects.filter(job_id=job_id).exists():
                JobObject.objects.filter(id=job_id).delete()

        return Response({
            "status": "deleted",
            "deleted_chain_id": chain.chain_code,
            "deleted_jobs": [str(jid) for jid in set(job_ids)]
        }, status=status.HTTP_200_OK)
