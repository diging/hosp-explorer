from ask.models import Conversation


def sidebar_conversations(request):
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(
            user=request.user
        ).prefetch_related("qa_records")[:50]

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
                "updated_at": conv.updated_at,
            })
        return {"sidebar_conversations": sidebar_items}
    return {"sidebar_conversations": []}
