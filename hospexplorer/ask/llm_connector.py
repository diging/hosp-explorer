import requests
from django.conf import settings

def query_llm(query):
    headers = {
        "X-API-Key": settings.LLM_TOKEN,
        "Content-Type": "application/json",
    }

    payload = {
        "input": query
    }

    response = requests.post(settings.LLM_HOST, json=payload, headers=headers, timeout=300)

    response.raise_for_status()  # raises on 4xx/5xx
    return response.json()