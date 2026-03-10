import json
import logging
import threading

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from ask.models import Conversation, QARecord, QueryTask, TermsAcceptance
from ask.tasks import run_llm_task

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
@require_POST
def query(request):
    """
    Accept a user query via POST, create a background task, return task_id.
    The LLM call runs in a background thread to avoid HTTP timeouts.
    """
    try:
        body = json.loads(request.body)
        query_text = body.get("query", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    if not query_text:
        return JsonResponse({"error": "No query provided."}, status=400)

    conversation_id = body.get("conversation_id")
    if conversation_id:
        conversation = get_object_or_404(
            Conversation, id=conversation_id, user=request.user
        )
    else:
        conversation = Conversation.objects.filter(user=request.user).first()
        if not conversation:
            conversation = Conversation.objects.create(user=request.user)

    record = QARecord.objects.create(
        conversation=conversation,
        question_text=query_text,
        user=request.user,
    )

    # conversation title is set from the first question
    if not conversation.title:
        conversation.title = query_text[:200]
        conversation.save()

    task = QueryTask.objects.create(
        user=request.user,
        query_text=query_text,
        status=QueryTask.Status.PENDING,
    )

    thread = threading.Thread(
        target=run_llm_task,
        args=(task.id, record.id, conversation.id),
        daemon=True,
    )
    thread.start()

    return JsonResponse({
        "task_id": str(task.id),
        "conversation_id": conversation.id,
        "conversation_title": conversation.title,
    })


@login_required
@require_GET
def poll_query(request, task_id):
    """Return the current status of a QueryTask. Only the owning user can poll."""
    try:
        task = QueryTask.objects.get(pk=task_id, user=request.user)
    except QueryTask.DoesNotExist:
        return JsonResponse({"error": "Task not found."}, status=404)

    response_data = {"status": task.status}

    if task.status == QueryTask.Status.COMPLETED:
        response_data["message"] = task.result
    elif task.status == QueryTask.Status.FAILED:
        response_data["error"] = task.error_message

    return JsonResponse(response_data)



@login_required
def terms_accept(request):
    current_version = settings.TERMS_VERSION
    already_accepted = TermsAcceptance.objects.filter(
        user=request.user,
        terms_version=current_version,
    ).exists()

    if already_accepted:
        request.session["terms_accepted_version"] = current_version
        return redirect("ask:index")

    if request.method == "POST":
        TermsAcceptance.objects.create(
            user=request.user,
            terms_version=current_version,
        )
        request.session["terms_accepted_version"] = current_version
        return redirect("ask:index")

    return render(request, "terms/terms_accept.html", {
        "terms_version": current_version,
    })


@login_required
def terms_view(request):
    current_version = settings.TERMS_VERSION
    acceptance = TermsAcceptance.objects.filter(
        user=request.user,
        terms_version=current_version,
    ).first()

    # Terms are stored in templates/terms/terms_of_use_content.html and is easily editable.
    # TERMS_VERSION in settings.py is used to track the version of the terms. The middleware checks each user's accepted
    # version (cached in session) against TERMS_VERSION anytime there is a mismatch, it redirects
    # them to terms_accept, where a new TermsAcceptance record is created with their IP and timestamp before they can access the app again.

    return render(request, "terms/terms_view.html", {
        "terms_version": current_version,
        "acceptance": acceptance,
    })


@login_required
@require_http_methods(["DELETE"])
def delete_history(request):
    request.user.conversations.all().delete()
    return JsonResponse({"message": "All conversations deleted successfully!"})
