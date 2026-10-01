from rest_framework.permissions import AllowAny
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import JobObject, ScriptRevision, PromptSet, Platform
from .serializers import JobObjectSerializer, PromptSetSerializer, PlatformSerializer

class PlatformViewSet(viewsets.ModelViewSet):
    queryset = Platform.objects.all().order_by('label')
    serializer_class = PlatformSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'label', 'description']


class JobStudioViewSet(viewsets.ModelViewSet):
    queryset = JobObject.objects.all().prefetch_related('revisions', 'prompts')
    serializer_class = JobObjectSerializer
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'title', 'tags']

    # --- CATEGORY A: OBJECT MANAGEMENT ---
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """API: Clone a JOBS object."""
        original = self.get_object()

        with transaction.atomic():
            clone = JobObject.objects.create(
                name=f"{original.name}_COPY",
                title=f"Copy of {original.title}",
                platform=original.platform,
                platform_obj=original.platform_obj,
                owner=request.user
            )

            latest = original.revisions.filter(version=original.active_revision).first()
            if latest is None:
                latest = original.revisions.order_by('-version').first()

            if latest is None:
                return Response({'error': 'Original job has no revisions to duplicate.'}, status=400)

            ScriptRevision.objects.create(
                job_object=clone,
                version=1,
                content=latest.content,
                created_by=request.user
            )

            prompt_copies = [
                PromptSet(
                    job_object=clone,
                    variable_name=prompt.variable_name,
                    label=prompt.label,
                    field_type=prompt.field_type,
                    default_value=prompt.default_value,
                )
                for prompt in original.prompts.all()
            ]
            PromptSet.objects.bulk_create(prompt_copies)

        return Response(JobObjectSerializer(clone).data, status=201)

    # --- CATEGORY B: VERSIONING (PROCESS) ---

    @action(detail=True, methods=['post'], url_path='rollback')
    def rollback(self, request, pk=None):
        """API: Revert to a specific version number."""
        job = self.get_object()
        version_num = request.data.get('version')
        if version_num is None:
            return Response({'error': 'version is required'}, status=400)

        try:
            version_num = int(version_num)
        except (TypeError, ValueError):
            return Response({'error': 'version must be an integer'}, status=400)

        if job.revisions.filter(version=version_num).exists():
            job.active_revision = version_num
            job.save()
            return Response({'status': f'Active version set to {version_num}'})
        return Response({'error': 'Version not found'}, status=404)

    # --- CATEGORY C: PROMPTS (VARIABLES) ---

    @action(detail=True, methods=['get', 'post'], url_path='prompts')
    def manage_prompts(self, request, pk=None):
        job = self.get_object()
        if request.method == 'GET':
            return Response(PromptSetSerializer(job.prompts.all(), many=True).data)
        
        serializer = PromptSetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(job_object=job)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    # --- CATEGORY D: BULK & UTILS ---

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        JobObject.objects.filter(id__in=ids).delete()
        return Response(status=204)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export job as JSON for AppWorx/Automic portability."""
        job = self.get_object()
        data = JobObjectSerializer(job).data
        return Response(data)

    permission_classes = [AllowAny]