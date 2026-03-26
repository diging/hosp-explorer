import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def list_kb_documents(page=1, page_size=10):
    """Call MCP KB docs/list endpoint. Returns parsed JSON response.

    Response format: {total, page, page_size, documents: [{id, title, url, chunks: [...]}]}
    """
    headers = {
        "Authorization": f"Bearer {settings.KB_MCP_JWT_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{settings.KB_MCP_HOST}/docs/list"
    params = {"page": page, "page_size": page_size}

    with httpx.Client() as client:
        response = client.get(
            url,
            headers=headers,
            params=params,
            timeout=settings.KB_MCP_TIMEOUT,
        )

    response.raise_for_status()
    return response.json()
