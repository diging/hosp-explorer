import httpx
from django.conf import settings


def query_llm(query):
    headers = {
        "Authorization": f"Bearer {settings.LLM_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.7,
        "max_tokens": settings.LLM_MAX_TOKENS
    }

    with httpx.Client() as client:
        response = client.post(
            settings.LLM_HOST + settings.LLM_QUERY_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=settings.LLM_TIMEOUT
        )

    response.raise_for_status()
    return response.json()