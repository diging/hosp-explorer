from django.db import models
from django.conf import settings


class TermsAcceptance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="terms_acceptances",
    )
    terms_version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

    class Meta:
        ordering = ["-accepted_at"]
        indexes = [
            models.Index(fields=["user", "terms_version"]),
        ]

    def __str__(self):
        return f"{self.user.username} accepted v{self.terms_version} on {self.accepted_at}"
