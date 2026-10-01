from django.urls import path , include 
from rest_framework.routers import DefaultRouter
from .views import JobStudioViewSet, PlatformViewSet


router=DefaultRouter()
router.register(r'objects', JobStudioViewSet, basename='studio-objects')
router.register(r'platforms', PlatformViewSet, basename='studio-platforms')

urlpatterns = [
    path('', include(router.urls)),
]