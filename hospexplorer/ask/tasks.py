import logging

from django.db import close_old_connections
from django.utils import timezone

import ask.llm_connector
from ask.models import Conversation, QARecord, QueryTask, WebsiteResource


logger = logging.getLogger(__name__)


def run_llm_task(task_id, record_id, conversation_id):
    """Background thread that calls the LLM and writes the result to the DB."""
    try:
        task = QueryTask.objects.get(pk=task_id)
        task.status = QueryTask.Status.PROCESSING
        task.save(update_fields=["status", "updated_at"])

        record = QARecord.objects.get(pk=record_id)
        conversation = Conversation.objects.get(pk=conversation_id)

        # get all website resources for the conversation
        # values_list("url", flat=True) fetches only the url column and returns
        # plain strings instead of single element tuples
        # in llm_connector.py, urls is allowed to be an empty list if there
        # are no website resources for the conversation to prevent backend errors
        urls = list(WebsiteResource.objects.values_list("url", flat=True))
        llm_response = ask.llm_connector.query_llm(task.query_text, urls=urls, conversation_id=conversation_id)

        if not llm_response.get("success") or "output" not in llm_response:
            raise ValueError("LLM response is missing structure")

        content = llm_response["output"].get("content", "")

        task.result = content
        task.status = QueryTask.Status.COMPLETED
        task.save(update_fields=["result", "status", "updated_at"])

        record.answer_text = content
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        # touch conversation updated_at so it stays as the most recent
        conversation.save()
    except Exception:
        logger.exception("Background LLM task failed for task_id=%s", task_id)
        try:
            task = QueryTask.objects.get(pk=task_id)
            task.status = QueryTask.Status.FAILED
            task.error_message = "Something went wrong. Please try again."
            task.save(update_fields=["status", "error_message", "updated_at"])

            QARecord.objects.filter(pk=record_id).update(
                is_error=True,
                answer_text="Something went wrong. Please try again.",
                answer_timestamp=timezone.now(),
            )
        except Exception:
            logger.exception("Failed to mark task as failed, task_id=%s", task_id)
    finally:
        close_old_connections()
