from django.urls import re_path
from ask import views

app_name = "ask"

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^mock$", views.mock_response, name="mock-response"),
    re_path(r"^query$", views.query, name="query-llm"),
    re_path(r"^terms/$", views.terms_view, name="terms-view"),
    re_path(r"^terms/accept/$", views.terms_accept, name="terms-accept"),
    re_path(r"^history/delete$", views.delete_history, name="delete-history"),
]
