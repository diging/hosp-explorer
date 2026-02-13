import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import ask.llm_connector
from ask.models import QARecord

logger = logging.getLogger(__name__)

@login_required
def index(request):
    recent_questions = list(
        QARecord.objects.filter(user=request.user).values('id', 'question_text')[:10]
    )
    return render(request, "index.html", {
        'recent_questions_json': json.dumps(recent_questions, default=str)
    })


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
        if "choices" not in llm_response or not llm_response["choices"]:
            raise ValueError("LLM response is missing structure")
        answer_text = llm_response["choices"][0].get("message", {}).get("content", "")

        record.answer_text = answer_text
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        return JsonResponse({"message": answer_text})
    except (KeyError, IndexError, TypeError, ValueError) as e:
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
