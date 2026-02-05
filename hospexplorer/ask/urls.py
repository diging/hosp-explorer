from django.urls import path
from ask import views

app_name = "ask"

urlpatterns = [
    path("", views.index, name="index"),
    path("mock", views.mock_response, name="mock-response"),
    path("query", views.query, name="query-llm"),
]