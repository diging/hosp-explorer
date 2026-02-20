import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import ask.llm_connector
from ask.models import TermsAcceptance, QARecord
from ask.utils import _get_client_ip

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
        if "choices" not in llm_response or not llm_response["choices"]:
            raise ValueError("LLM response is missing structure")
        answer_text = llm_response["choices"][0].get("message", {}).get("content", "")

        record.answer_text = answer_text
        record.answer_raw_response = llm_response
        record.answer_timestamp = timezone.now()
        record.save()

        return JsonResponse({"message": answer_text})
    except (KeyError, IndexError, TypeError, ValueError) as e:
        # logger.exception() logs the exception and the stack trace
        logger.exception(f"Unexpected response from server {e}")
        error_msg = f"Unexpected response from server: {e}"
    except Exception as e:
        logger.exception(f"Failed to connect to server {e}")
        error_msg = f"Failed to connect to server: {e}"

    # The try block returns on success, so this only runs on error.
    record.is_error = True
    record.answer_text = error_msg
    record.answer_timestamp = timezone.now()
    record.save()
    return JsonResponse({"error": error_msg}, status=500)


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
        ip_address = _get_client_ip(request)
        TermsAcceptance.objects.create(
            user=request.user,
            terms_version=current_version,
            ip_address=ip_address,
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
