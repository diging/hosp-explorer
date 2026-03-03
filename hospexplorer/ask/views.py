import json
import logging
import threading

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from ask.models import QueryTask, QARecord
from ask.tasks import run_llm_task


logger = logging.getLogger(__name__)


@login_required
def index(request):
    recent_questions = list(
        QARecord.objects.filter(user=request.user)
        .order_by('-question_timestamp')
        .values('id', 'question_text')[:settings.RECENT_QUESTIONS_LIMIT]
    )
    return render(request, "index.html", {
        'recent_questions_json': json.dumps(recent_questions, default=str)
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
def submit_query(request):
    """Accept a query, create a task, spawn a background thread, return task ID."""
    try:
        body = json.loads(request.body)
        query_text = body.get("query", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    if not query_text:
        return JsonResponse({"error": "Query is required."}, status=400)

    task = QueryTask.objects.create(
        user=request.user,
        query_text=query_text,
        status=QueryTask.Status.PENDING,
    )

    thread = threading.Thread(target=run_llm_task, args=(task.id,), daemon=True)
    thread.start()

    return JsonResponse({"task_id": str(task.id)})


@login_required
@require_GET
def poll_query(request, task_id):
    """Return the current status of a QueryTask. Only the owning user can poll."""
    try:
        task = QueryTask.objects.get(pk=task_id, user=request.user)
    except QueryTask.DoesNotExist:
        return JsonResponse({"error": "Task not found."}, status=404)

    response_data = {
        "task_id": str(task.id),
        "status": task.status,
    }

    if task.status == QueryTask.Status.COMPLETED:
        response_data["result"] = task.result
    elif task.status == QueryTask.Status.FAILED:
        response_data["error"] = task.error_message

    return JsonResponse(response_data)


@login_required
@require_http_methods(["DELETE"])
def delete_history(request):
    request.user.qa_records.all().delete()
    return JsonResponse({"message": "Question history deleted successfully!"})
