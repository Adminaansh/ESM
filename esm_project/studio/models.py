from django.db import models
from django.conf import settings

AUTH_METHOD_CHOICES = [
    ('NONE', 'No Authentication'),
    ('PASSWORD', 'Password / Bearer Token'),
    ('SSH_KEY', 'SSH Key'),
]

class Platform(models.Model):
    PLATFORM_TYPE_CHOICES = [
        ('SSH', 'SSH / Linux Server'),
        ('WINRM', 'Windows Remote'),
        ('SQL', 'Database Instance'),
        ('SAP', 'SAP System'),
        ('API', 'External API'),
        ('LOCAL', 'Local Execution'),
    ]

    AUTH_METHOD_CHOICES = AUTH_METHOD_CHOICES

    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    platform_type = models.CharField(max_length=20, choices=PLATFORM_TYPE_CHOICES, default='LOCAL')
    host = models.CharField(max_length=255, blank=True, help_text='Target host address, server name, or API base URL')
    port = models.PositiveIntegerField(null=True, blank=True, default=22)
    username = models.CharField(max_length=255, blank=True)
    auth_method = models.CharField(max_length=20, choices=AUTH_METHOD_CHOICES, default='NONE')
    secret_reference = models.CharField(max_length=255, blank=True, help_text='Vault reference key for password, bearer token, or SSH key content')
    api_url = models.URLField(blank=True, help_text='External API endpoint URL')
    api_method = models.CharField(max_length=10, blank=True, default='POST', help_text='HTTP method when platform_type is API')
    api_headers = models.TextField(blank=True, help_text='JSON string of request headers for external API')
    api_body_template = models.TextField(blank=True, help_text='Request body template for the external API invocation')
    api_callback_path = models.CharField(max_length=255, blank=True, help_text='Callback path for external apps to report completion')
    api_callback_secret = models.CharField(max_length=255, blank=True, help_text='Shared secret used by the external callback')
    api_timeout_seconds = models.PositiveIntegerField(default=600, help_text='Seconds to wait for external API completion callback')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_secret(self):
        if not self.secret_reference:
            return ''
        try:
            from vault.models import SecuredVariable
            variable = SecuredVariable.objects.get(reference_key=self.secret_reference.strip().upper())
            return variable.get_secret()
        except Exception:
            return ''

    def __str__(self):
        return f"{self.label} ({self.code})"


class JobObject(models.Model):
    """Equivalent to Automic 'JOBS'. The master identity of a task."""
    PLATFORM_CHOICES = [
        ('UNIX', 'Unix/Linux'),
        ('WINDOWS', 'Windows'),
        ('SQL', 'Database Query'),
        ('SAP', 'SAP R/3'),
    ]
    SCRIPT_LANGUAGE_CHOICES = [
        ('BASH', 'Bash'),
        ('PYTHON', 'Python'),
    ]

    name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='UNIX')
    platform_obj = models.ForeignKey('Platform', null=True, blank=True, on_delete=models.SET_NULL, related_name='job_objects')
    script_language = models.CharField(max_length=20, choices=SCRIPT_LANGUAGE_CHOICES, default='BASH')
    remote_host = models.CharField(max_length=255, blank=True, help_text='Optional remote host for direct SSH execution')
    remote_port = models.PositiveIntegerField(null=True, blank=True, default=22)
    remote_username = models.CharField(max_length=255, blank=True)
    remote_auth_method = models.CharField(max_length=20, choices=AUTH_METHOD_CHOICES, default='NONE')
    remote_secret_reference = models.CharField(max_length=255, blank=True, help_text='Optional vault reference key for remote authentication')
    is_active = models.BooleanField(default=True)
    active_revision = models.PositiveIntegerField(default=1)
    tags = models.JSONField(default=list, blank=True)
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_secret(self):
        if not self.remote_secret_reference:
            return ''
        try:
            from vault.models import SecuredVariable
            variable = SecuredVariable.objects.get(reference_key=self.remote_secret_reference.strip().upper())
            return variable.get_secret()
        except Exception:
            return ''

    def __str__(self):
        return f"{self.name} ({self.platform_obj.code if self.platform_obj else self.platform})"

class ScriptRevision(models.Model):
    """The 'Process' tab. Stores every version of the code logic."""
    job_object = models.ForeignKey(JobObject, related_name='revisions', on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    content = models.TextField()  # The actual script
    pre_process = models.TextField(blank=True) # Logic run before execution
    post_process = models.TextField(blank=True) # Logic run after execution
    change_summary = models.CharField(max_length=255, blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job_object', 'version')

class PromptSet(models.Model):
    """Dynamic UI variables requested at runtime (PRPT)."""
    job_object = models.ForeignKey(JobObject, related_name='prompts', on_delete=models.CASCADE)
    variable_name = models.CharField(max_length=100) # e.g. &DATE#
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=50, default='text') # text, date, number
    default_value = models.CharField(max_length=255, blank=True, null=True)