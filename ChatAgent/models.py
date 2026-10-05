from django.db import models
import secrets, hashlib
from core.models import User

# Create your models here.
class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=50)
    key_hash = models.CharField(max_length=128, unique=True, editable=False)
    prefix = models.CharField(max_length=8, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    @classmethod
    def generate_key(cls, user, name):
        """
        Generates a new API key.
        Returns a tuple: (APIKey instance, raw_key string)
        """
        # Generate a cryptographically secure random token
        raw_key = f"sk_kora_{secrets.token_urlsafe(16)}"
        prefix = raw_key[:8]
        
        # Hash the token with SHA-256 before saving
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key_obj = cls.objects.create(
            user=user,
            name=name,
            prefix=prefix,
            key_hash=key_hash
        )
        
        # Return raw_key ONLY ONCE to show the user
        return api_key_obj, raw_key

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"