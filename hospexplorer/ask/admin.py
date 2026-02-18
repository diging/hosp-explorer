from django.contrib import admin
from ask.models import TermsAcceptance


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
