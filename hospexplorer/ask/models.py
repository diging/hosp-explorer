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


class QARecord(models.Model):
    """
    Stores a question-answer pair from user interactions with the LLM.
    """
    # Question fields
    question_text = models.TextField()
    question_timestamp = models.DateTimeField(auto_now_add=True)

    # Answer fields
    answer_text = models.TextField(blank=True, default="")
    answer_raw_response = models.JSONField(default=dict)
    answer_timestamp = models.DateTimeField(null=True, blank=True)
    is_error = models.BooleanField(default=False)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qa_records")

    class Meta:
        ordering = ["-question_timestamp"]
        verbose_name = "Q&A Record"
        verbose_name_plural = "Q&A Records"
        indexes = [
            models.Index(fields=["user", "-question_timestamp"]),
        ]

    def __str__(self):
        truncated = self.question_text[:50]
        suffix = "..." if len(self.question_text) > 50 else ""
        return f"{self.user.username}: {truncated}{suffix}"
