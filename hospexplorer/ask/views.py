import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone

import ask.llm_connector
from ask.models import Conversation, QARecord

logger = logging.getLogger(__name__)


@login_required
def index(request):
    return render(request, "index.html")


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
def mock_response(request):
    """Returns a mock LLM response in the same format as the real server."""
    return JsonResponse({
        "success": True,
        "output": {
            "content": "Under the shimmering moonlit sky, a silver-maned unicorn named Luna trotted through the enchanted forest, her hooves leaving trails of stardust. When she discovered a wounded fox whimpering beneath an ancient oak, she touched her glowing horn to its paw, weaving magic that healed the hurt. With the fox curled beside her, Luna rested on a bed of moss, her heart full as the forest whispered lullabies, ensuring all creatures drifted into dreams of peace."
        }
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

    # Set conversation title from the first question
    if not conversation.title:
        conversation.title = query_text[:200]

    try:
        llm_response = ask.llm_connector.query_llm(query_text)

        # Mock and real LLM use the same response format
        # response format {"success": true, "output": {"content": ""}}
        if not llm_response.get("success") or "output" not in llm_response:
            raise ValueError("LLM response is missing structure")
        answer_text = llm_response["output"].get("content", "")

        record.answer_text = answer_text
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        # Touch updated_at so this conversation stays as the most recent
        conversation.save()

        return JsonResponse({"message": answer_text, "conversation_id": conversation.id, "conversation_title": conversation.title})
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
    return JsonResponse({"error": error_msg, "conversation_id": conversation.id, "conversation_title": conversation.title}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_history(request):
    request.user.qa_records.all().delete()
    return JsonResponse({"message": "Question history deleted successfully!"})
