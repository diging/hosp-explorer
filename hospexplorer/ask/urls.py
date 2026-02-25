from django.urls import path
from ask import views

app_name = "ask"

urlpatterns = [
    path("", views.index, name="index"),
    path("mock", views.mock_response, name="mock-response"),
    path("submit", views.submit_query, name="submit-query"),
    path("poll/<uuid:task_id>", views.poll_query, name="poll-query"),
]