from django.conf import settings


def terms_status(request):
    if hasattr(request, "user") and request.user.is_authenticated:
        accepted = request.session.get("terms_accepted_version") == settings.TERMS_VERSION
        return {"terms_accepted": accepted, "terms_version": settings.TERMS_VERSION}
    return {}
