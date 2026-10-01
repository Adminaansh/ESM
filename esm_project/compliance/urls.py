# apps/compliance/urls.py
from django.urls import path
from .views import AutomatedLogArchivalSweepAPI, EmitSecurityAuditEventAPI

urlpatterns = [
    path('archive/sweep/', AutomatedLogArchivalSweepAPI.as_view(), name='compliance-sweep'),
    path('audit/incident/', EmitSecurityAuditEventAPI.as_view(), name='compliance-incident'),
]