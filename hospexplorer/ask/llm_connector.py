import httpx
from django.conf import settings


def _get_endpoint():
    from ask.models import SimWorkflow
    active = SimWorkflow.get_active()
    if active and active.agent_endpoint:
        return active.agent_endpoint
    return settings.LLM_HOST


def query_llm(query):
    headers = {
        "X-API-Key": settings.LLM_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {
        "input": query
    }

    endpoint = _get_endpoint()

    with httpx.Client() as client:
        response = client.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=settings.LLM_TIMEOUT
        )

    response.raise_for_status()
    return response.json()
