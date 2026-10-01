# apps/scheduler/models.py
import uuid
from uuid import UUID
from django.db import models

class AutomatedSchedule(models.Model):
    """
    Automated Trigger Rules. Configures rules for when workflow chains 
    should be executed by background workers without human input.
    """
    TRIGGER_TYPE_CHOICES = [
        ('INTERVAL', 'Fixed Interval (Seconds)'),
        ('CHRONOLOGICAL', 'Fixed Daily Time (HH:MM)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Target workflow blueprint reference identifier (From Module 3: Engine)
    chain_id = models.CharField(max_length=20)
    name = models.CharField(max_length=255, unique=True)
    
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, default='INTERVAL')
    
    # Rule Parameters (Evaluated conditionally by views/workers)
    interval_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="e.g., 30 for every half-minute")
    fixed_time = models.TimeField(null=True, blank=True, help_text="Specific time of day to fire target workflow")
    
    # State tracking metrics
    is_enabled = models.BooleanField(default=True)
    last_fired_at = models.DateTimeField(null=True, blank=True)
    next_expected_fire = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Normalize saved references to chain_code for safer long-term scheduler targeting.
        if self.chain_id:
            from engine.models import Chain

            normalized = None
            if str(self.chain_id).isdigit():
                normalized = Chain.objects.filter(chain_code=int(self.chain_id)).first()
            else:
                try:
                    guid = UUID(str(self.chain_id))
                    normalized = Chain.objects.filter(chain_guid=guid).first()
                except Exception:
                    normalized = None

            if normalized:
                self.chain_id = str(normalized.chain_code)
            else:
                raise ValueError(f"Unable to resolve chain reference for AutomatedSchedule: {self.chain_id}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Schedule: {self.name} -> Target Chain: {self.chain_id}"


class TriggerIncidentLog(models.Model):
    """
    Audit log for tracking automated scheduler trigger evaluation metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(AutomatedSchedule, on_delete=models.CASCADE, related_name="incidents")
    
    # Tracking references spawned on successful execution
    spawned_execution_id = models.UUIDField(null=True, blank=True, help_text="Linked Process ID from Module 5")
    
    was_successful = models.BooleanField(default=True)
    error_details = models.TextField(null=True, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status_string = "SUCCESS" if self.was_successful else "FAILED"
        return f"Incident {self.id} [{status_string}] - {self.evaluated_at}"