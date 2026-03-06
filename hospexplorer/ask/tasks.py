import logging

from django.db import close_old_connections
from django.utils import timezone

import ask.llm_connector
from ask.models import QueryTask, QARecord, WebsiteResource


logger = logging.getLogger(__name__)


def run_llm_task(task_id):
    """Background thread that calls the LLM and writes the result to the DB."""
    try:
        task = QueryTask.objects.get(pk=task_id)
        task.status = QueryTask.Status.PROCESSING
        task.save(update_fields=["status", "updated_at"])

        # Create QARecord to persist the Q&A history
        record = QARecord.objects.create(
            question_text=task.query_text,
            user=task.user,
        )

        urls = list(WebsiteResource.objects.values_list("url", flat=True))
        llm_response = ask.llm_connector.query_llm(task.query_text, urls=urls)
        content = llm_response["output"].get("content", "")

        task.result = content
        task.status = QueryTask.Status.COMPLETED
        task.save(update_fields=["result", "status", "updated_at"])

        # Update QARecord with the answer
        record.answer_text = content
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()
    except Exception:
        logger.exception("Background LLM task failed for task_id=%s", task_id)
        try:
            task = QueryTask.objects.get(pk=task_id)
            task.status = QueryTask.Status.FAILED
            task.error_message = "Something went wrong. Please try again."
            task.save(update_fields=["status", "error_message", "updated_at"])

            # Mark QARecord as error if it was created
            QARecord.objects.filter(
                question_text=task.query_text,
                user=task.user,
                is_error=False,
                answer_text="",
            ).update(
                is_error=True,
                answer_text="Something went wrong. Please try again.",
                answer_timestamp=timezone.now(),
            )
        except Exception:
            logger.exception("Failed to mark task as failed, task_id=%s", task_id)
    finally:
        close_old_connections()
