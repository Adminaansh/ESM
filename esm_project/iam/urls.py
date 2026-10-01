from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import *

router =DefaultRouter()
router.register(r'users',UserViewset,basename='users')
router.register(r'roles',RoleViewSet,basename='roles')
router.register(r'permission',PermissionListView, basename='permissions')
router.register(r'keys',APIKeyViewSet, basename='keys')

urlpatterns=[
    path('',include(router.urls)),
    path('authlogout/',LogoutView.as_view(), name='logout'),
    path('auth/mfa/',MFAView.as_view(),name='mfa'),
    path('sso/config/',SSOConfigView.as_view(),name='sso'),
]