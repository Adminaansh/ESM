# apps/maintenance/models.py
import uuid
from django.db import models

class MaintenancePolicy(models.Model):
    """
    Automated System Rules. Configures automatic retention policies 
    for telemetry data and system logs.
    """
    SUBSYSTEM_CHOICES = [
        ('LIVE_LOGS', 'Active Execution Logs (Module 5)'),
        ('HEARTBEATS', 'Telemetry Pings (Module 4)'),
        ('INCIDENTS', 'Audit Incident Records (Module 8)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subsystem = models.CharField(max_length=30, choices=SUBSYSTEM_CHOICES, unique=True)
    
    retention_days = models.PositiveIntegerField(default=30, help_text="Age threshold before data is automatically purged")
    is_active = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Policy for {self.get_subsystem_display()} -> {self.retention_days} Days"


class CleanupExecutionLog(models.Model):
    """
    Performance Metrics Log. Records data cleanup events, track optimization metrics,
    and monitors database size health.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(MaintenancePolicy, on_delete=models.SET_NULL, null=True, related_name="runs")
    
    rows_deleted = models.PositiveIntegerField(default=0)
    space_reclaimed_mb = models.FloatField(default=0.0)
    
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status_str = "SUCCESS" if self.was_successful else "FAILED"
        return f"Purge Engine {self.id} [{status_str}] - Deleted {self.rows_deleted} rows"