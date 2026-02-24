from django.conf import settings
from django.urls import reverse
from ask.models import Conversation


def sidebar_conversations(request):
    if request.user.is_authenticated:
        limit = getattr(settings, "SIDEBAR_CONVERSATIONS_LIMIT", 10)
        conversations = Conversation.objects.filter(
            user=request.user
        ).prefetch_related("qa_records")[:limit]

        sidebar_items = []
        for conv in conversations:
            first_qa = conv.qa_records.order_by("question_timestamp").first()
            if first_qa:
                label = first_qa.question_text[:40]
                if len(first_qa.question_text) > 40:
                    label += "..."
            else:
                label = conv.created_at.strftime("%b %d, %Y %I:%M %p")
            sidebar_items.append({
                "id": conv.id,
                "label": label,
                "url": reverse("ask:conversation", kwargs={"conversation_id": conv.id}),
                "updated_at": conv.updated_at.isoformat(),
            })
        return {
            "sidebar_conversations": sidebar_items,
            "sidebar_conversations_limit": limit,
        }
    return {"sidebar_conversations": [], "sidebar_conversations_limit": 0}
