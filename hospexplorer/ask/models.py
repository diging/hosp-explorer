import uuid

from django.conf import settings
from django.db import models

# Abstract Model, fields are inherited by subclasses
class Resource(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s_created",
    )
    modifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_modified",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title


class WebsiteResource(Resource):
    url = models.URLField()

    class Meta:
        verbose_name = "Website Resource"
        verbose_name_plural = "Website Resources"


class QueryTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="query_tasks",
    )
    query_text = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    result = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        if self.title:
            truncated = self.title[:50]
            suffix = "..." if len(self.title) > 50 else ""
            return f"Conversation {self.id}: {truncated}{suffix}"
        return f"Conversation {self.id} ({self.user.username})"


class TermsAcceptance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="terms_acceptances",
    )
    terms_version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(auto_now_add=True)

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
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="qa_records",
    )

    # Question fields
    question_text = models.TextField()
    question_timestamp = models.DateTimeField(auto_now_add=True)

    # Answer fields
    answer_text = models.TextField(blank=True, default="")
    answer_raw_response = models.JSONField(default=dict)
    answer_timestamp = models.DateTimeField(null=True, blank=True)
    is_error = models.BooleanField(default=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="qa_records",
    )

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
