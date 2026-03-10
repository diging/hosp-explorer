from django.contrib import admin
from ask.models import Conversation, TermsAcceptance, QARecord, WebsiteResource


class QARecordInline(admin.TabularInline):
    model = QARecord
    extra = 0
    readonly_fields = ("question_text", "question_timestamp", "answer_text", "answer_timestamp", "is_error")
    fields = ("question_text", "question_timestamp", "answer_text", "answer_timestamp", "is_error")


class SuperuserOnlyMixin:
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Conversation)
class ConversationAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_filter = ("user",)
    search_fields = ("title", "user__username")
    inlines = [QARecordInline]


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    list_display = ("user", "terms_version", "accepted_at")
    list_filter = ("terms_version", "accepted_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "terms_version", "accepted_at")
    ordering = ("-accepted_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QARecord)
class QARecordAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    list_display = ["id", "user", "conversation", "truncated_question", "question_timestamp", "answer_timestamp", "is_error"]
    list_filter = ["question_timestamp", "user", "is_error"]
    search_fields = ["question_text", "answer_text", "user__username"]
    readonly_fields = ["question_timestamp", "answer_timestamp", "answer_raw_response"]
    raw_id_fields = ["user", "conversation"]
    date_hierarchy = "question_timestamp"

    def truncated_question(self, obj):
        return obj.question_text[:75] + "..." if len(obj.question_text) > 75 else obj.question_text
    truncated_question.short_description = "Question"


@admin.register(WebsiteResource)
class WebsiteResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "url", "creator", "modified_at")
    search_fields = ("title", "url")
    readonly_fields = ("created_at", "modified_at", "creator", "modifier")
    help_texts = {
        "title": "A short name to identify this website resource.",
        "description": "Optional details about what this website covers.",
        "url": "The URL the LLM will use as context when answering questions.",
    }

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name, text in self.help_texts.items():
            if field_name in form.base_fields:
                form.base_fields[field_name].help_text = text
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator = request.user
        obj.modifier = request.user
        super().save_model(request, obj, form, change)
