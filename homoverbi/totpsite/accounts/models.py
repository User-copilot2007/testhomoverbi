from django.db import models
from django.contrib.auth.models import User

class PendingSignup(models.Model):
    """Holds the intermediate signup state until TOTP is confirmed."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="pending_signup")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PendingSignup(user={self.user.username})"


class EulaAcceptance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='eula_acceptance')
    accepted_at = models.DateTimeField(auto_now_add=True)
    document_sha256 = models.CharField(max_length=64)
    document_name = models.CharField(max_length=255, default='eula.pdf')

    def __str__(self):
        return f"EulaAcceptance(user={self.user.username}, at={self.accepted_at})"
