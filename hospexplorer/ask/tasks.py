import logging

import httpx
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

import ask.llm_connector
from ask.models import Conversation, QARecord, QueryTask


logger = logging.getLogger(__name__)


def run_llm_task(task_id, record_id, conversation_id):
    """Background thread that calls the LLM and writes the result to the DB."""
    try:
        task = QueryTask.objects.get(pk=task_id)
        task.status = QueryTask.Status.PROCESSING
        task.save(update_fields=["status", "updated_at"])

        record = QARecord.objects.get(pk=record_id)
        conversation = Conversation.objects.get(pk=conversation_id)

        # pass the UUID (not the integer PK) as the LLM backend conversation identifier
        llm_response = ask.llm_connector.query_llm(task.query_text, llm_conversation_id=conversation.llm_conversation_id)

        if not llm_response.get("success") or "output" not in llm_response:
            raise ValueError("LLM response is missing structure")

        # content is a JSON string with search_results from the LLM
        # sent to frontend as is, parsed on the frontend by window.renderChatMessage() in index.html
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


def run_kb_resource_upload(model_label, resource_id):
    """Background thread: push a resource to the MCP KB and record its doc_id.

    Runs outside the admin's atomic save transaction so a slow or timing-out
    MCP call can't roll back the local row. The object's status/status_message
    are updated at each phase so the admin can surface progress and errors.
    """
    from ask.models import WebsiteResource, PDFResource, Resource
    from ask.kb_connector import add_pdf_to_kb, add_website_to_kb

    if model_label == "pdf":
        Model = PDFResource
    elif model_label == "website":
        Model = WebsiteResource
    else:
        logger.error("run_kb_resource_upload: unknown model_label=%r", model_label)
        return

    try:
        obj = Model.objects.get(pk=resource_id)
    except Model.DoesNotExist:
        logger.error("run_kb_resource_upload: %s id=%s not found", model_label, resource_id)
        return

    try:
        if model_label == "pdf":
            obj.file.open("rb")
            try:
                file_bytes = obj.file.read()
            finally:
                obj.file.close()
            result = add_pdf_to_kb(file_bytes, obj.file.name.split("/")[-1], obj.title)
        else:
            result = add_website_to_kb(obj.url)

        obj.mcp_kb_document_id = result.get("doc_id")
        obj.status = Resource.Status.SUCCESS
        obj.status_message = f"Uploaded to Knowledge Base (doc_id={obj.mcp_kb_document_id})."
        obj.save(update_fields=["mcp_kb_document_id", "status", "status_message"])
    except httpx.TimeoutException:
        logger.exception("Background KB %s upload timed out for resource_id=%s", model_label, resource_id)
        obj.status = Resource.Status.ERROR
        obj.status_message = (
            f"Upload timed out after {settings.KB_MCP_TIMEOUT}s. "
            "The Knowledge Base did not finish processing this file in time — "
            "it may be too large. Edit the resource and save again to retry."
        )
        obj.save(update_fields=["status", "status_message"])
    except Exception as e:
        logger.exception("Background KB %s upload failed for resource_id=%s", model_label, resource_id)
        obj.status = Resource.Status.ERROR
        obj.status_message = f"Upload to Knowledge Base failed: {e}"[:1000]
        obj.save(update_fields=["status", "status_message"])
    finally:
        close_old_connections()
