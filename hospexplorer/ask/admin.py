from django.contrib import admin
from ask.models import Conversation, TermsAcceptance, QARecord, SimWorkflow


class QARecordInline(admin.TabularInline):
    model = QARecord
    extra = 0
    readonly_fields = ("question_text", "question_timestamp", "answer_text", "answer_timestamp", "is_error")
    fields = ("question_text", "question_timestamp", "answer_text", "answer_timestamp", "is_error")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_filter = ("user",)
    search_fields = ("title", "user__username")
    inlines = [QARecordInline]


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(admin.ModelAdmin):
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
class QARecordAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "conversation", "truncated_question", "question_timestamp", "answer_timestamp", "is_error"]
    list_filter = ["question_timestamp", "user", "is_error"]
    search_fields = ["question_text", "answer_text", "user__username"]
    readonly_fields = ["question_timestamp", "answer_timestamp", "answer_raw_response"]
    raw_id_fields = ["user", "conversation"]
    date_hierarchy = "question_timestamp"

    def truncated_question(self, obj):
        return obj.question_text[:75] + "..." if len(obj.question_text) > 75 else obj.question_text
    truncated_question.short_description = "Question"


@admin.register(SimWorkflow)
class SimWorkflowAdmin(admin.ModelAdmin):
    list_display = ("title", "workflow_id", "workflow_type", "is_active", "agent_endpoint", "updated_at")
    list_filter = ("is_active", "workflow_type")
    search_fields = ("title", "description", "workflow_id")
    actions = ["set_as_active"]
    fieldsets = (
        (None, {
            "fields": ("title", "description", "workflow_id", "workflow_type"),
        }),
        ("Endpoint", {
            "fields": ("agent_endpoint",),
            "description": "The active workflow's endpoint is used by the LLM connector. "
                           "If no workflow is active or the endpoint is blank, the LLM_HOST env variable is used as fallback.",
        }),
        ("Status", {
            "fields": ("is_active",),
            "description": "Only one workflow can be active at a time. "
                           "Activating this workflow will deactivate all others. "
                           "You cannot deactivate or delete the last active workflow.",
        }),
    )

    # action to select exactly one workflow and activate it
    # the model's save() will auto-deactivate all others
    @admin.action(description="Set selected workflow as active")
    def set_as_active(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one workflow to activate.", level="error")
            return
        workflow = queryset.first()
        workflow.is_active = True
        workflow.save()
        self.message_user(request, f"'{workflow.title}' is now the active workflow.")

    # catches ValidationError from model constraints
    # and gives an admin message instead of a 500 error
    def save_model(self, request, obj, form, change):
        from django.core.exceptions import ValidationError
        try:
            obj.save()
        except ValidationError as e:
            self.message_user(request, e.message, level="error")

    # catches ValidationError when trying to delete the only active workflow.
    def delete_model(self, request, obj):
        from django.core.exceptions import ValidationError
        try:
            obj.delete()
        except ValidationError as e:
            self.message_user(request, e.message, level="error")

    # handles bulk delete; deletes one by one so the active workflow constraint is checked per object
    # stops if the only active workflow is being deleted
    def delete_queryset(self, request, queryset):
        from django.core.exceptions import ValidationError
        for obj in queryset:
            try:
                obj.delete()
            except ValidationError as e:
                self.message_user(request, e.message, level="error")
                return
