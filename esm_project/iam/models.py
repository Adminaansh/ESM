import uuid
from django.db import models
from django.contrib.auth.models import User

class Role(models.Model):
    """
    Defines system roles like 'Admin', 'Scheduler', 'Operator', 'Viewer'
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Permissions stored as JSON for flexibility (e.g., {"can_kill_job": True})
    permissions = models.JSONField(default=dict)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    """
    Extends the default Django User to include Roles
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.role.name if self.role else 'No Role'}"
    

class APIKey(models.Model):
    User = models.ForeignKey(User, on_delete=models.CASCADE ,related_name='api_keys')
    name = models.CharField(max_length=100) 
    key = models.CharField(max_length=128,unique=True) # Hashed key
    prefix = models.CharField(max_length=8,unique=True) # First 8 chars for identification
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True) 
     
    def __str__(self):
        return f"{self.name}({self.User.username})"  
