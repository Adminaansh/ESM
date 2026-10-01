# apps/compliance/models.py
import uuid
from django.db import models

class HistoricalExecutionArchive(models.Model):
    """
    Automated Data Janitor. Stores flattened, historical summaries of completed 
    processes after operational cleanup routines purge them from active tables.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Original structural execution references tracking indices
    original_execution_id = models.UUIDField(unique=True)
    process_no = models.PositiveIntegerField(unique=True)
    chain_id = models.CharField(max_length=20)
    
    final_status = models.CharField(max_length=20)
    triggered_by = models.CharField(max_length=255)
    
    # Combined, aggregated log file text payload containing all stdout frames
    compiled_console_output = models.TextField(help_text="Flattened history dump file")
    
    # Chronological metrics
    execution_duration_seconds = models.FloatField(default=0.0)
    archived_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Archive - Process #{self.process_no} ({self.final_status})"


class SecurityAuditEvent(models.Model):
    """
    Automated Compliance Watchdog. Tracks structural system events, security anomalies, 
    and policy breaches across your ESM tool.
    """
    AUDIT_SEVERITY_CHOICES = [
        ('LOW', 'Informational Change'),
        ('MEDIUM', 'Suspicious Activity'),
        ('HIGH', 'Critical Security Breach'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subsystem = models.CharField(max_length=50, help_text="e.g., 'VAULT', 'INFRASTRUCTURE'")
    event_type = models.CharField(max_length=100, help_text="e.g., 'UNAUTHORIZED_KEY_LOOKUP'")
    severity = models.CharField(max_length=10, choices=AUDIT_SEVERITY_CHOICES, default='LOW')
    
    metadata_json = models.JSONField(default=dict, help_text="Contextual event indicators")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity}] {self.subsystem} -> {self.event_type} at {self.timestamp}"