# apps/infrastructure/models.py
import uuid
from django.db import models

class InfrastructureTarget(models.Model):
    """
    Automated Infrastructure Nodes. Represents machines, servers, or cloud tasks 
    dynamically discovered and managed by the ESM platform.
    """
    TARGET_TYPE_CHOICES = [
        ('LINUX_SERVER', 'Linux Node'),
        ('WINDOWS_SERVER', 'Windows Node'),
        ('CONTAINER', 'Docker/K8s Container'),
        ('DATABASE', 'Database Instance'),
    ]

    STATUS_CHOICES = [
        ('HEALTHY', 'Healthy'),
        ('UNHEALTHY', 'Unhealthy / High Load'),
        ('OFFLINE', 'Offline / Unreachable'),
        ('DRAINING', 'Draining / Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Reported hostname of the machine")
    target_type = models.CharField(max_length=30, choices=TARGET_TYPE_CHOICES, default='LINUX_SERVER')
    
    # Network address details reported automatically during handshake
    host_address = models.GenericIPAddressField(protocol='both', unpack_ipv4=True, unique=True)
    
    # Auto-calculated health metrics updated via telemetry heartbeats
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='HEALTHY')
    cpu_utilization = models.FloatField(default=0.0)
    memory_utilization = models.FloatField(default=0.0)
    
    # Chronological tracking
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.host_address}) -> {self.status}"


class RemoteAgentSession(models.Model):
    """
    Tracks active runtime connection parameters for authenticated edge agents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.OneToOneField(InfrastructureTarget, on_delete=models.CASCADE, related_name="session")
    agent_version = models.CharField(max_length=20)
    secure_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Active Session for {self.target.name}"