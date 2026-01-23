import requests
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
        "max_tokens": 1000
    }

    response = requests.post(settings.LLM_HOST + settings.LLM_QUERY_ENDPOINT, json=payload, headers=headers, timeout=60)

    response.raise_for_status()  # raises on 4xx/5xx
    print(response)
    return response.json()