from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import ChainViewSet

# The router handles the trailing slashes and IDs automatically
router = DefaultRouter()
router.register(r'chains', ChainViewSet, basename='chain')

urlpatterns=[
    path('',include(router.urls)),
]