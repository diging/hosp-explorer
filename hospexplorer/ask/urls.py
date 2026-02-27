from django.urls import path, re_path
from ask import views

app_name = "ask"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new_conversation, name="new-conversation"),
    path("c/<int:conversation_id>/", views.conversation_detail, name="conversation"),
    path("query/", views.query, name="query-llm"),
    re_path(r"^mock$", views.mock_response, name="mock-response"),
    re_path(r"^history/delete$", views.delete_history, name="delete-history"),
]
