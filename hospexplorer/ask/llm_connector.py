import httpx
from django.conf import settings


def query_llm(query):
    headers = {
        "X-API-Key": settings.LLM_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {
        "input": query
    }

    with httpx.Client() as client:
        response = client.post(
            settings.LLM_HOST,
            json=payload,
            headers=headers,
            timeout=settings.LLM_TIMEOUT
        )

    response.raise_for_status()
    return response.json()
