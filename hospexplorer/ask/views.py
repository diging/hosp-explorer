import asyncio
import logging
import threading

from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

import ask.llm_connector
from ask.models import QueryTask


logger = logging.getLogger(__name__)


def _run_llm_task(task_id):
    """Background thread that calls the LLM and writes the result to the DB."""
    try:
        task = QueryTask.objects.get(pk=task_id)
        task.status = QueryTask.Status.PROCESSING
        task.save(update_fields=["status", "updated_at"])

        llm_response = asyncio.run(ask.llm_connector.query_llm(task.query_text))
        content = llm_response["choices"][0]["message"]["content"]

        task.result = content
        task.status = QueryTask.Status.COMPLETED
        task.save(update_fields=["result", "status", "updated_at"])
    except Exception:
        logger.exception("Background LLM task failed for task_id=%s", task_id)
        try:
            task = QueryTask.objects.get(pk=task_id)
            task.status = QueryTask.Status.FAILED
            task.error_message = "Something went wrong. Please try again."
            task.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            logger.exception("Failed to mark task as failed, task_id=%s", task_id)
    finally:
        close_old_connections()


@login_required
def index(request):
    return render(request, "index.html", {})


@login_required
def mock_response(request):
    return JsonResponse({
        "message": "Okay, the user wants a three-sentence bedtime story about a unicorn. Let's start by thinking about the key elements of a good bedtime story. They usually have a peaceful setting, a gentle conflict or quest, and a happy ending.\n\nFirst sentence needs to set the scene. Maybe a magical forest with a unicorn. Luna is a common unicorn name, sounds soft. Moonlight and stars could add a calming effect.\n\nSecond sentence should introduce a small problem or something the unicorn does. Healing powers are typical for unicorns. Maybe she finds an injured animal, like a fox. Using her horn to heal adds magic.\n\nThird sentence wraps it up with a happy ending. The fox recovers, they become friends, and the forest is peaceful. Emphasize safety and dreams to make it soothing for bedtime.\n\nCheck if it's exactly three sentences. Yes. Language is simple and comforting, suitable for a child. Avoid any scary elements. Make sure it flows smoothly and conveys warmth.\n</think>\n\nUnder the shimmering moonlit sky, a silver-maned unicorn named Luna trotted through the enchanted forest, her hooves leaving trails of stardust. When she discovered a wounded fox whimpering beneath an ancient oak, she touched her glowing horn to its paw, weaving magic that healed the hurt. With the fox curled beside her, Luna rested on a bed of moss, her heart full as the forest whispered lullabies, ensuring all creatures drifted into dreams of peace."
    })


@login_required
async def query(request):
    try:
        llm_response = await ask.llm_connector.query_llm(request.GET["query"])
        content = llm_response["choices"][0]["message"]["content"]
        return JsonResponse({"message": content})
    except Exception:
        logger.exception("Failed to query LLM")
        return JsonResponse({"error": "Something went wrong. Please try again."}, status=500)


@login_required
@require_GET
def submit_query(request):
    """Accept a query, create a task, spawn a background thread, return task ID."""
    query_text = request.GET.get("query", "").strip()
    if not query_text:
        return JsonResponse({"error": "Query is required."}, status=400)

    task = QueryTask.objects.create(
        user=request.user,
        query_text=query_text,
        status=QueryTask.Status.PENDING,
    )

    thread = threading.Thread(target=_run_llm_task, args=(task.id,), daemon=True)
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
