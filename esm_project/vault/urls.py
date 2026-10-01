# apps/vault/urls.py
from django.urls import path
from .views import InjectSecretVariableAPI, FetchSecretVariableAPI

urlpatterns = [
    path('secret/inject/', InjectSecretVariableAPI.as_view(), name='vault-inject'),
    path('secret/resolve/', FetchSecretVariableAPI.as_view(), name='vault-resolve'),
]