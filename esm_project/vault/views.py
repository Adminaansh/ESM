# apps/vault/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import SecuredVariable

class InjectSecretVariableAPI(APIView):
    """
    AUTOMATED ENCRYPTED INJECTION
    Endpoint: POST /api/vault/secret/inject/
    Fired by CI/CD setups or administrative tools to securely save or rotate values.
    """
    def post(self, request):
        key = request.data.get("key")
        raw_value = request.data.get("value")
        notes = request.data.get("description", "")

        if not key or not raw_value:
            return Response({"error": "Key and Value parameters required"}, status=status.HTTP_400_BAD_REQUEST)

        # Upsert pattern: locate existing key or initialize a fresh model instance
        variable, created = SecuredVariable.objects.get_or_create(
            reference_key=key.strip().upper(),
            defaults={"description": notes}
        )

        # Encrypt data using model helper method before executing save
        variable.set_secret(str(raw_value))
        if not created and notes:
            variable.description = notes
        variable.save()

        return Response({
            "status": "parameter_secured",
            "reference_key": variable.reference_key,
            "action_executed": "ENCRYPTED_NEW_ROW" if created else "ROTATED_EXISTING_CIPHER",
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)


class FetchSecretVariableAPI(APIView):
    """
    RUNTIME PARAMETER RESOLUTION
    Endpoint: POST /api/vault/secret/resolve/
    Called strictly by the runtime execution engine when spawning scripts to map environment variables.
    """
    def post(self, request):
        key = request.data.get("key")
        # System Validation: Expects a secure engine runner system signature passkey token
        runner_token = request.data.get("runner_token") 

        if not key or not runner_token:
            return Response({"error": "Missing lookup identifier or access signature"}, status=status.HTTP_400_BAD_REQUEST)

        # NOTE: Implement an internal verification step matching your execution context here 
        # (e.g., verifying that runner_token belongs to an active tracking sequence in Module 5)

        try:
            variable = SecuredVariable.objects.get(reference_key=key.strip().upper())
        except SecuredVariable.DoesNotExist:
            return Response({"error": f"Secured variable target '{key}' not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "reference_key": variable.reference_key,
            "resolved_plaintext_value": variable.get_secret(), # Decrypted dynamically on extraction
            "fetched_at": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)