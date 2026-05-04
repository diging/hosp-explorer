import json
import logging

from django.db import close_old_connections
from django.utils import timezone

import ask.llm_connector
from ask.models import Conversation, PDFResource, QARecord, QueryTask, WebsiteResource


logger = logging.getLogger(__name__)


def _infer_type_from_url(url):
    """Failsafe for results that don't match any local resource (untracked KB docs).
    The MCP KB only stores a url for websites, so a missing url is treated as PDF."""
    if not url or not isinstance(url, str) or not url.strip():
        return "PDF"
    path = url.split("?", 1)[0].split("#", 1)[0]
    if path.lower().endswith(".pdf"):
        return "PDF"
    return "Website"


def _normalize_doc_id(value):
    """normalize a document_id to an int, or None if it can't be resolved
    The LLM emits the chunk-level "[doc_id]-[chunk_index]" id string
    in this slot, so we accept that shape and fall back to its primary number"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip().split("-", 1)[0])
        except ValueError:
            return None
    return None


def _enrich_search_results(content):
    """Match each search_result's document_id to local PDFResource/WebsiteResource and tag it with
    a human-friendly type. PDFs also get their url rewritten to the local file URL."""
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content
    results = payload.get("search_results")
    if not isinstance(results, list) or not results:
        return content

    # normalize document_id on each result up front so the rest of the function can rely
    # on it being an int or None (the LLM sometimes hands us strings like "12-3")
    for r in results:
        r["document_id"] = _normalize_doc_id(r.get("document_id"))

    # collect all mcp document ids referenced in this batch of results so we can
    # look them up in a single query per resource type instead of per result
    doc_ids = {r["document_id"] for r in results if r["document_id"] is not None}

    # pdf_by_doc_id keeps the full PDFResource so we can also rewrite the url to the local file
    # for websites we only need the set of matched ids since the original url is fine to keep
    pdf_by_doc_id = {}
    website_doc_ids = set()
    if doc_ids:
        pdf_by_doc_id = {
            p.mcp_kb_document_id: p
            for p in PDFResource.objects.filter(mcp_kb_document_id__in=doc_ids)
        }
        website_doc_ids = set(
            WebsiteResource.objects.filter(mcp_kb_document_id__in=doc_ids).values_list(
                "mcp_kb_document_id", flat=True
            )
        )

    # tag each result with a type and rewrite PDF urls to the local file
    for r in results:
        doc_id = r["document_id"]
        pdf = pdf_by_doc_id.get(doc_id)
        if pdf is not None:
            if pdf.file:
                r["url"] = pdf.file.url
            r["type"] = "PDF"
        elif doc_id in website_doc_ids:
            r["type"] = "Website"
        else:
            r["type"] = _infer_type_from_url(r.get("url"))

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
        
        # tag each search result with a type and link PDF hits at the local PDFResource
        content = _enrich_search_results(content)

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
