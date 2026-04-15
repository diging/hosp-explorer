import logging

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


def run_kb_pdf_upload(pdf_resource_id):
    """Background thread: upload a PDFResource's file to the MCP KB and
    record the returned doc_id on the local row.

    Runs outside the admin's atomic save transaction so a slow or timing-out
    MCP call can't roll back the local PDFResource insert. If this fails
    (e.g. MCP down, timeout), mcp_kb_document_id stays null and the
    existing reconciliation UI surfaces it as unsynced.
    """
    from ask.models import PDFResource
    from ask.kb_connector import add_pdf_to_kb
    try:
        obj = PDFResource.objects.get(pk=pdf_resource_id)
        obj.file.open("rb")
        try:
            file_bytes = obj.file.read()
        finally:
            obj.file.close()
        result = add_pdf_to_kb(file_bytes, obj.file.name.split("/")[-1], obj.title)
        obj.mcp_kb_document_id = result.get("doc_id")
        obj.save(update_fields=["mcp_kb_document_id"])
    except Exception:
        logger.exception("Background KB PDF upload failed for pdf_resource_id=%s", pdf_resource_id)
    finally:
        close_old_connections()


def run_kb_website_upload(website_resource_id):
    """Background thread: send a WebsiteResource's URL to the MCP KB and
    record the returned doc_id. See run_kb_pdf_upload for rationale.
    """
    from ask.models import WebsiteResource
    from ask.kb_connector import add_website_to_kb
    try:
        obj = WebsiteResource.objects.get(pk=website_resource_id)
        result = add_website_to_kb(obj.url)
        obj.mcp_kb_document_id = result.get("doc_id")
        obj.save(update_fields=["mcp_kb_document_id"])
    except Exception:
        logger.exception("Background KB website upload failed for website_resource_id=%s", website_resource_id)
    finally:
        close_old_connections()
