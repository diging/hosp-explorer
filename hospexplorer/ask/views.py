import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ask.models import Conversation, Message
import ask.llm_connector


@login_required
def index(request):
    """Landing page: redirect to the most recent conversation, or show empty state."""
    latest = Conversation.objects.filter(user=request.user).first()
    if latest:
        return redirect("ask:conversation", conversation_id=latest.id)
    return render(request, "index.html", {
        "conversation": None,
        "messages_json": "[]",
    })


@login_required
@require_POST
def new_conversation(request):
    """Create a new blank conversation and redirect to it."""
    conversation = Conversation.objects.create(user=request.user)
    return redirect("ask:conversation", conversation_id=conversation.id)


@login_required
def conversation_detail(request, conversation_id):
    """Display an existing conversation with all its messages."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )
    messages = conversation.messages.all()
    messages_json = json.dumps([
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ])
    return render(request, "index.html", {
        "conversation": conversation,
        "messages_json": messages_json,
    })


@login_required
@require_POST
def query(request):
    """
    Accept a user query via POST, save it and the LLM response to the DB.
    Expects JSON body: {"query": "...", "conversation_id": <int|null>}
    Returns JSON: {"message": "...", "conversation_id": <int>}
    """
    try:
        body = json.loads(request.body)
        user_query = body["query"]
        conversation_id = body.get("conversation_id")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse(
            {"error": "Invalid request body. Expected JSON with 'query' field."},
            status=400,
        )

    # Get or create conversation
    if conversation_id:
        conversation = get_object_or_404(
            Conversation, id=conversation_id, user=request.user
        )
    else:
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

    # Touch updated_at so this conversation floats to top of sidebar
    conversation.save()

    return JsonResponse({
        "message": content,
        "conversation_id": conversation.id,
    })


@login_required
@require_POST
def delete_conversation(request, conversation_id):
    """Delete a conversation owned by the current user."""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )
    conversation.delete()
    return redirect("ask:index")
