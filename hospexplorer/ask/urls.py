from django.contrib import admin
from django.urls import path
from ask import views

urlpatterns = [
    path("", views.index),
    path("query", views.mock_response, name="mock-response")
]