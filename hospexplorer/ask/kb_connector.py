import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def add_website_to_kb(url):
    """Send a website URL to the MCP KB server for ingestion.

    Calls POST /docs/website/add?url={url} on the MCP KB server.
    The KB server fetches the page, chunks it, generates embeddings,
    and stores it for semantic search.
    """
    headers = {
        "Authorization": f"Bearer {settings.KB_MCP_JWT_TOKEN}",
    }
    endpoint = f"{settings.KB_MCP_HOST}/docs/website/add"

    with httpx.Client() as client:
        response = client.post(
            endpoint,
            params={"url": url},
            headers=headers,
            timeout=settings.KB_MCP_TIMEOUT,
        )

    response.raise_for_status()
    return response.json()
