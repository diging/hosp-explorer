from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import ask.llm_connector


# Create your views here.
def index(request):
    return render(request, "index.html", {})

def mock_response(request):
    return JsonResponse({
        "message": "Okay, the user wants a three-sentence bedtime story about a unicorn. Let's start by thinking about the key elements of a good bedtime story. They usually have a peaceful setting, a gentle conflict or quest, and a happy ending.\n\nFirst sentence needs to set the scene. Maybe a magical forest with a unicorn. Luna is a common unicorn name, sounds soft. Moonlight and stars could add a calming effect.\n\nSecond sentence should introduce a small problem or something the unicorn does. Healing powers are typical for unicorns. Maybe she finds an injured animal, like a fox. Using her horn to heal adds magic.\n\nThird sentence wraps it up with a happy ending. The fox recovers, they become friends, and the forest is peaceful. Emphasize safety and dreams to make it soothing for bedtime.\n\nCheck if it's exactly three sentences. Yes. Language is simple and comforting, suitable for a child. Avoid any scary elements. Make sure it flows smoothly and conveys warmth.\n</think>\n\nUnder the shimmering moonlit sky, a silver-maned unicorn named Luna trotted through the enchanted forest, her hooves leaving trails of stardust. When she discovered a wounded fox whimpering beneath an ancient oak, she touched her glowing horn to its paw, weaving magic that healed the hurt. With the fox curled beside her, Luna rested on a bed of moss, her heart full as the forest whispered lullabies, ensuring all creatures drifted into dreams of peace."
    })

async def query(request):
    try:
        llm_response = await ask.llm_connector.query_llm(request.GET["query"])
        content = llm_response["choices"][0]["message"]["content"]
        return render(request, "_response.html", {"message": content})
    except Exception:
        return render(request, "_response.html", {"message": "Something went wrong. Please try again."})