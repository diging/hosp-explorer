from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import ask.llm_connector
from ask.models import QARecord


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
    return JsonResponse({
        "message": "Okay, the user wants a three-sentence bedtime story about a unicorn. Let's start by thinking about the key elements of a good bedtime story. They usually have a peaceful setting, a gentle conflict or quest, and a happy ending.\n\nFirst sentence needs to set the scene. Maybe a magical forest with a unicorn. Luna is a common unicorn name, sounds soft. Moonlight and stars could add a calming effect.\n\nSecond sentence should introduce a small problem or something the unicorn does. Healing powers are typical for unicorns. Maybe she finds an injured animal, like a fox. Using her horn to heal adds magic.\n\nThird sentence wraps it up with a happy ending. The fox recovers, they become friends, and the forest is peaceful. Emphasize safety and dreams to make it soothing for bedtime.\n\nCheck if it's exactly three sentences. Yes. Language is simple and comforting, suitable for a child. Avoid any scary elements. Make sure it flows smoothly and conveys warmth.\n</think>\n\nUnder the shimmering moonlit sky, a silver-maned unicorn named Luna trotted through the enchanted forest, her hooves leaving trails of stardust. When she discovered a wounded fox whimpering beneath an ancient oak, she touched her glowing horn to its paw, weaving magic that healed the hurt. With the fox curled beside her, Luna rested on a bed of moss, her heart full as the forest whispered lullabies, ensuring all creatures drifted into dreams of peace."
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

        answer_text = ""
        if "choices" in llm_response and llm_response["choices"]:
            answer_text = llm_response["choices"][0].get("message", {}).get("content", "")
        elif "message" in llm_response:
            answer_text = llm_response["message"]

        record.answer_text = answer_text
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        return JsonResponse({"message": answer_text})
    except (KeyError, IndexError, TypeError) as e:
        error_msg = f"Unexpected response from server: {e}"
    except Exception as e:
        error_msg = f"Failed to connect to server: {e}"

    # The try block returns on success, so this only runs on error.
    record.is_error = True
    record.answer_text = error_msg
    record.answer_timestamp = timezone.now()
    record.save()
    return JsonResponse({"error": error_msg}, status=500)
