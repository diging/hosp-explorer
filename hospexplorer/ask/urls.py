from django.contrib import admin
from django.urls import path
from ask import views

urlpatterns = [
    path("", views.index),
    path("mock", views.mock_response, name="mock-response"),
    path("query", views.query, name="query-llm")
]