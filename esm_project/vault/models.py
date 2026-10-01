# apps/vault/models.py
import uuid
import os
from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings

# System Fallback: In production, ensure VAULT_SECRET_KEY is stored securely in environment variables
_VAULT_KEY = getattr(settings, "VAULT_SECRET_KEY", None)
if not _VAULT_KEY:
    # Generates a temporary stable string for local development environments if not explicitly configured
    _VAULT_KEY = Fernet.generate_key().decode()

cipher_suite = Fernet(_VAULT_KEY.encode())

class SecuredVariable(models.Model):
    """
    Encrypted Parameter Vault. Stores database credentials, API secrets, 
    and configurations safely.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Human-readable reference label used by workflow engines to request a variable value
    reference_key = models.CharField(max_length=255, unique=True, db_index=True)
    
    # The actual string contents are stored strictly as encrypted byte arrays in the DB row
    encrypted_value = models.TextField(help_text="AES-256 cipher string data")
    
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_secret(self, raw_plaintext_string):
        """Encrypts a plain text string before storing it in the database."""
        if raw_plaintext_string:
            self.encrypted_value = cipher_suite.encrypt(raw_plaintext_string.encode()).decode()

    def get_secret(self):
        """Decrypts the database string back into accessible plain text on-the-fly."""
        if self.encrypted_value:
            return cipher_suite.decrypt(self.encrypted_value.encode()).decode()
        return ""

    def __str__(self):
        return f"Secured Lock -> {self.reference_key}"