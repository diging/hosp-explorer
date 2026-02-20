import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone

import ask.llm_connector
from ask.models import Conversation, QARecord

logger = logging.getLogger(__name__)


@login_required
def index(request):
    return render(request, "index.html", {})


@login_required
@require_POST
def new_conversation(request):
    """Create a new blank conversation and redirect to it."""
    conversation = Conversation.objects.create(user=request.user)
    return redirect("ask:conversation", conversation_id=conversation.id)


@login_required
def conversation_detail(request, conversation_id):
    """Display an existing conversation with all its QA records."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )
    return render(request, "index.html", {
        "conversation": conversation,
    })


@login_required
def query(request):
    """
    Accept a user query via GET, save it and the LLM response as a QARecord.
    Uses the conversation specified by conversation_id, or the most recent one,
    or creates a new one if none exist.
    """
    query_text = request.GET.get("query", "")
    if not query_text:
        return JsonResponse({"error": "No query provided."}, status=400)

    # Get or create conversation
    conversation_id = request.GET.get("conversation_id")
    if conversation_id:
        conversation = get_object_or_404(
            Conversation, id=conversation_id, user=request.user
        )
    else:
        conversation = Conversation.objects.filter(user=request.user).first()
        if not conversation:
            conversation = Conversation.objects.create(user=request.user)

    # Create QARecord with the question
    record = QARecord.objects.create(
        conversation=conversation,
        question_text=query_text,
        user=request.user,
    )

    try:
        llm_response = ask.llm_connector.query_llm(query_text)

        if "choices" not in llm_response or not llm_response["choices"]:
            raise ValueError("LLM response is missing structure")
        answer_text = llm_response["choices"][0].get("message", {}).get("content", "")

        record.answer_text = answer_text
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        # Touch updated_at so this conversation stays as the most recent
        conversation.save()

        return JsonResponse({"message": answer_text, "conversation_id": conversation.id})
    except (KeyError, IndexError, TypeError, ValueError) as e:
        logger.exception("Unexpected response from server: %s", e)
        error_msg = f"Unexpected response from server: {e}"
    except Exception as e:
        logger.exception("Failed to connect to server: %s", e)
        error_msg = f"Failed to connect to server: {e}"

    # The try block returns on success, so this only runs on error.
    record.is_error = True
    record.answer_text = error_msg
    record.answer_timestamp = timezone.now()
    record.save()
    return JsonResponse({"error": error_msg, "conversation_id": conversation.id}, status=500)
