from django.shortcuts import render


def client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def render_form(request, form, title, *, back_url=None, submit_label="Save", intro=None):
    """Generic form page (core/form.html) so simple CRUD screens need no template."""
    return render(
        request,
        "core/form.html",
        {"form": form, "title": title, "back_url": back_url, "submit_label": submit_label, "intro": intro},
    )


def render_confirm(request, title, message, *, back_url=None, submit_label="Confirm"):
    """Generic POST-confirmation page (deletes, closes, etc.)."""
    return render(
        request,
        "core/confirm.html",
        {"title": title, "message": message, "back_url": back_url, "submit_label": submit_label},
    )
