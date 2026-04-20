import json
import logging

from django.db import close_old_connections
from django.utils import timezone

import ask.llm_connector
from ask.models import Conversation, PDFResource, QARecord, QueryTask


logger = logging.getLogger(__name__)


def _enrich_pdf_urls(content):
    """Match each search_result's document_id to a local PDFResource and rewrite
    its url to the PDF's file URL """
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content
    results = payload.get("search_results")
    if not isinstance(results, list) or not results:
        return content

    doc_ids = {r.get("document_id") for r in results if r.get("document_id") is not None}
    if not doc_ids:
        return content

    pdf_by_doc_id = {
        p.mcp_kb_document_id: p
        for p in PDFResource.objects.filter(mcp_kb_document_id__in=doc_ids)
    }
    for r in results:
        pdf = pdf_by_doc_id.get(r.get("document_id"))
        if pdf is not None and pdf.file:
            r["url"] = pdf.file.url

    return json.dumps(payload)


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
        
        # pdf hits to link at the local PDFResource
        content = _enrich_pdf_urls(content)

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
