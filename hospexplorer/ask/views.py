from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ask.models import Conversation, Message
import ask.llm_connector


@login_required
def index(request):
    return render(request, "index.html", {})


@login_required
@require_POST
def new_conversation(request):
    """Create a new blank conversation and redirect to the index."""
    Conversation.objects.create(user=request.user)
    return redirect("ask:index")


@login_required
def conversation_detail(request, conversation_id):
    """Display an existing conversation with all its messages."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )
    return render(request, "index.html", {
        "conversation": conversation,
    })


@login_required
def query(request):
    """
    Accept a user query via GET, save it and the LLM response to the DB.
    Uses the user's most recent conversation, or creates one if none exist.
    """
    user_query = request.GET.get("query", "")
    if not user_query:
        return JsonResponse({"error": "No query provided."}, status=400)

    # Get the most recent conversation or create one
    conversation = Conversation.objects.filter(user=request.user).first()
    if not conversation:
        conversation = Conversation.objects.create(user=request.user)

    # Save user message
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=user_query,
    )

    # Query LLM
    try:
        llm_response = ask.llm_connector.query_llm(user_query)
        content = llm_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        content = f"Unexpected response from server: {e}"
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=content,
        )
        return JsonResponse({"error": content}, status=500)
    except Exception as e:
        content = f"Failed to connect to server: {e}"
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=content,
        )
        return JsonResponse({"error": content}, status=500)

    # Save assistant message
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=content,
    )

    # Touch updated_at so this conversation stays as the most recent
    conversation.save()

    return JsonResponse({"message": content})
