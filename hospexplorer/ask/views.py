import logging
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
import ask.llm_connector
from ask.models import QARecord

logger = logging.getLogger(__name__)

@login_required
def index(request):
    return render(request, "index.html", {})


@login_required
def mock_response(request):
    """Returns a mock LLM response in the same format as the real server."""
    return JsonResponse({
        "choices": [{
            "message": {
                "content": "Under the shimmering moonlit sky, a silver-maned unicorn named Luna trotted through the enchanted forest, her hooves leaving trails of stardust. When she discovered a wounded fox whimpering beneath an ancient oak, she touched her glowing horn to its paw, weaving magic that healed the hurt. With the fox curled beside her, Luna rested on a bed of moss, her heart full as the forest whispered lullabies, ensuring all creatures drifted into dreams of peace."
            }
        }]
    })

@login_required
def query(request):
    query_text = request.GET.get("query", "")
    record = QARecord.objects.create(
        question_text=query_text,
        user=request.user,
    )
    try:
        llm_response = ask.llm_connector.query_llm(query_text)

        # Mock and real LLM use the same response format
        answer_text = ""
        if "choices" in llm_response and llm_response["choices"]:
            answer_text = llm_response["choices"][0].get("message", {}).get("content", "")

        record.answer_text = answer_text
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        return JsonResponse({"message": answer_text})
    except (KeyError, IndexError, TypeError) as e:
        logger.exception("Unexpected response from server")
        error_msg = f"Unexpected response from server: {e}"
    except Exception as e:
        logger.exception("Failed to connect to server")
        error_msg = f"Failed to connect to server: {e}"

    # The try block returns on success, so this only runs on error.
    record.is_error = True
    record.answer_text = error_msg
    record.answer_timestamp = timezone.now()
    record.save()
    return JsonResponse({"error": error_msg}, status=500)

@login_required
@require_POST
def delete_history(request):
    request.user.qa_records.all().delete()
    messages.success(request, "Question history deleted successfully!")
    return redirect("ask:index")
