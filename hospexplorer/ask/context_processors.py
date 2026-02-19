from ask.models import Conversation


def sidebar_conversations(request):
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(
            user=request.user
        ).prefetch_related("messages")[:50]

        sidebar_items = []
        for conv in conversations:
            first_message = conv.messages.first()
            if first_message:
                label = first_message.content[:40]
                if len(first_message.content) > 40:
                    label += "..."
            else:
                label = conv.created_at.strftime("%b %d, %Y %I:%M %p")
            sidebar_items.append({
                "id": conv.id,
                "label": label,
                "updated_at": conv.updated_at,
            })
        return {"sidebar_conversations": sidebar_items}
    return {"sidebar_conversations": []}
