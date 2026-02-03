import httpx
from django.conf import settings


async def query_llm(query):
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
        "max_tokens": 1000
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.LLM_HOST + settings.LLM_QUERY_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=60
        )

    response.raise_for_status()
    return response.json()