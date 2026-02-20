from django.contrib import admin
from ask.models import TermsAcceptance, QARecord


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("user", "terms_version", "accepted_at", "ip_address")
    list_filter = ("terms_version", "accepted_at")
    search_fields = ("user__username", "user__email", "ip_address")
    readonly_fields = ("user", "terms_version", "accepted_at", "ip_address")
    ordering = ("-accepted_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QARecord)
class QARecordAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "truncated_question", "question_timestamp", "answer_timestamp"]
    list_filter = ["question_timestamp", "user"]
    search_fields = ["question_text", "answer_text", "user__username"]
    readonly_fields = ["question_timestamp", "answer_timestamp", "answer_raw_response"]
    raw_id_fields = ["user"]
    date_hierarchy = "question_timestamp"

    def truncated_question(self, obj):
        return obj.question_text[:75] + "..." if len(obj.question_text) > 75 else obj.question_text
    truncated_question.short_description = "Question"
