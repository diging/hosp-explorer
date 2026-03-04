from django.conf import settings


# Django context processor registered in settings TEMPLATES
# Injects terms_accepted (bool) and terms_version into every template context,
# reads from the session cache set by TermsAcceptanceMiddleware to avoid hitting the db on every request
def terms_status(request):
    if hasattr(request, "user") and request.user.is_authenticated:
        accepted = request.session.get("terms_accepted_version") == settings.TERMS_VERSION
        return {"terms_accepted": accepted, "terms_version": settings.TERMS_VERSION}
    return {}
