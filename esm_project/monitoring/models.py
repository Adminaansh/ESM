# apps/monitoring/models.py
import time
import uuid
from django.db import DatabaseError, IntegrityError, close_old_connections, models
from django.db import transaction
from django.utils import timezone

class WorkflowExecution(models.Model):
    """
    The Live Process Machine. Tracks every runtime instance of a executed 
    pipeline blueprint with custom state automation rules.
    """
    STATE_CHOICES = [
        ('QUEUED', 'Queued'),
        ('RUNNING', 'Running'),
        ('HOLD', 'Hold'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('TERMINATED', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Associated chain reference id (from Module 3: Engine)
    chain_id = models.CharField(max_length=20)
    
    # Human-readable sequential running tracking sequence index
    process_no = models.PositiveIntegerField(editable=False, unique=True)
    
    status = models.CharField(max_length=20, choices=STATE_CHOICES, default='QUEUED')
    triggered_by = models.CharField(max_length=255, default='SYSTEM_EVENT')
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Serially assign a sequential process number with retries on SQLite lock or collision.
        if not self.process_no:
            attempt = 0
            while True:
                try:
                    close_old_connections()
                    max_process = WorkflowExecution.objects.aggregate(
                        models.Max('process_no')
                    )['process_no__max']
                    self.process_no = (max_process or 0) + 1
                    super().save(*args, **kwargs)
                    break
                except IntegrityError as exc:
                    if attempt >= 5 or 'process_no' not in str(exc).lower():
                        raise
                    attempt += 1
                    time.sleep(0.1 * attempt)
                except DatabaseError as exc:
                    if attempt >= 5 or 'locked' not in str(exc).lower():
                        raise
                    attempt += 1
                    time.sleep(0.1 * attempt)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Process #{self.process_no} -> {self.status}"


class LiveExecutionLog(models.Model):
    """
    High-frequency append-only storage for streaming console execution logs.
    """
    LOG_LEVEL_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning Alert'),
        ('ERROR', 'Critical Failure'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="logs")
    
    node_id = models.UUIDField(null=True, blank=True, help_text="The exact step within the chain generating this output")
    log_level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.log_level}] Process #{self.execution.process_no} - {self.timestamp}"


class WorkflowExecutionHistory(models.Model):
    """
    Stores archived pipeline executions after they leave live monitoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_execution_id = models.UUIDField(null=True, blank=True)
    process_no = models.PositiveIntegerField()
    chain_id = models.CharField(max_length=20)
    chain_name = models.CharField(max_length=255, null=True, blank=True)
    task_name = models.CharField(max_length=255, null=True, blank=True)
    source = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    compiled_console_output = models.TextField(blank=True, default='')
    archived_at = models.DateTimeField(auto_now_add=True)


class ExternalAPITracking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('TIMED_OUT', 'Timed Out'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    step = models.OneToOneField('WorkflowExecutionStep', on_delete=models.CASCADE, related_name='external_tracking')
    external_job_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    callback_secret = models.CharField(max_length=255, blank=True)
    request_payload = models.TextField(blank=True, default='')
    response_summary = models.TextField(blank=True, default='')
    last_polled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ExternalAPITracking {self.external_job_id or self.id} -> {self.status}"

    class Meta:
        ordering = ['-updated_at']
    


class WorkflowExecutionStep(models.Model):
    """
    Tracks each chain node execution step as part of a running chain.
    """
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('TERMINATED', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='steps')
    node_id = models.UUIDField(null=True, blank=True)
    job_name = models.CharField(max_length=255)
    sequence_index = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sequence_index']

    def __str__(self):
        return f"Step {self.sequence_index} ({self.job_name}) -> {self.status}"

    @property
    def elapsed_minutes(self):
        if not self.started_at:
            return 0
        end_time = self.ended_at or timezone.now()
        return round((end_time - self.started_at).total_seconds() / 60, 1)
