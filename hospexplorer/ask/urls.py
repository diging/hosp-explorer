from django.urls import path
from ask import views

app_name = "ask"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new_conversation, name="new-conversation"),
    path("c/<int:conversation_id>/", views.conversation_detail, name="conversation"),
    path("c/<int:conversation_id>/delete/", views.delete_conversation, name="delete-conversation"),
    path("query/", views.query, name="query-llm"),
]
