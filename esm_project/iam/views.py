import secrets
from rest_framework import viewsets,permissions,status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User, Permission
from .models import Role, UserProfile, APIKey
from .serializers import *


# --- USER & ROLE MANAGEMENT (9 APIs) ---
class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes =[permissions.IsAdminUser]

    @action(detail=False, methods=['get'],permission_classes=[permissions.IsAuthenticated])
    def me(self, request):# GET /api/v1/iam/users/me/
        serializer =self.get_serializer(request.user)
        return Response(serializer.data)
    
class RoleViewSet(viewsets.ModelViewSet):
    queryset=Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes =[permissions.IsAdminUser]

class PermissionListView(viewsets.ReadOnlyModelViewSet): 
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]   



# --- AUTH & SECURITY (6 APIs) ---
class LogoutView(APIView):   # POST /api/v1/iam/auth/logout/
    def post(self,request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message":"Successfully logged out"}, status=200)
        except Exception: return Response(status=400)



class APIKeyViewSet(viewsets.ModelViewSet): # 3 APIs: List, Create, Delete  
       serializer_class = APIKeySerializer
       def get_queryset(self):return APIKey.objects.filter(user=self.request.user)
           
       
       def create (self,request):
           name = request.data.get('name','New Key')
           raw_key =secrets.token_urlsafe(32)  
           APIKey.objects.create(user=request.user, name=name, prefix=raw_key[:8], key=raw_key)
           return Response({"key": raw_key, "msg": "Copy this now!"}, status=201) 
       
class SSOConfigView(APIView): # GET /api/v1/iam/sso/config/
    def get(self, request):
        return Response({"provider": "Active Directory", "status": "Active"})

class MFAView(APIView): # POST /api/v1/iam/auth/mfa/
    def post(self, request):
        return Response({"status": "MFA verified"})       
