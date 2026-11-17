"""Mongo `notifications` CRUD.

Customer: read own, mark read (update), delete / clear (delete).
Admin: read all, delete any, broadcast (create).
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import admin_required
from core.mongo import NOTIFICATIONS, col, oid, to_view
from core.utils import render_form
from users.models import User

from .services import build_notification


def _scope(request, extra=None):
    """Customers only ever touch their own docs; admins can touch any."""
    q = dict(extra or {})
    if not request.user.is_bank_admin:
        q["userId"] = request.user.pk
    return q


@login_required
def notification_list(request):
    q = _scope(request)
    if request.GET.get("unread"):
        q["isRead"] = False
    docs = [to_view(d) for d in col(NOTIFICATIONS).find(q).sort("sentAt", -1).limit(200)]
    if request.user.is_bank_admin:
        names = dict(User.objects.filter(pk__in={d["userId"] for d in docs}).values_list("pk", "username"))
        for d in docs:
            d["username"] = names.get(d["userId"], "?")
    return render(request, "notifications/list.html", {"notifications": docs})


@login_required
@require_POST
def mark_read(request, notification_id):
    col(NOTIFICATIONS).update_one(_scope(request, {"_id": oid(notification_id)}),
                                  {"$set": {"isRead": True, "readAt": timezone.now()}})
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    res = col(NOTIFICATIONS).update_many({"userId": request.user.pk, "isRead": False},
                                         {"$set": {"isRead": True, "readAt": timezone.now()}})
    messages.success(request, f"{res.modified_count} marked as read.")
    return redirect("notifications:list")


@login_required
@require_POST
def delete(request, notification_id):
    col(NOTIFICATIONS).delete_one(_scope(request, {"_id": oid(notification_id)}))
    messages.success(request, "Notification dismissed.")
    return redirect("notifications:list")


@login_required
@require_POST
def clear_all(request):
    res = col(NOTIFICATIONS).delete_many({"userId": request.user.pk, "isRead": True})
    messages.success(request, f"{res.deleted_count} read notifications cleared.")
    return redirect("notifications:list")


class BroadcastForm(forms.Form):
    recipient = forms.CharField(
        required=False, help_text="Username of one customer. Leave blank to send to ALL active customers."
    )
    title = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)
    category = forms.ChoiceField(choices=[(c, c) for c in ("BROADCAST", "INFO", "SECURITY")])

    def clean_recipient(self):
        username = self.cleaned_data["recipient"].strip()
        if username and not User.objects.filter(username=username).exists():
            raise forms.ValidationError("No such user.")
        return username


@admin_required
def broadcast(request):
    form = BroadcastForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if data["recipient"]:
            ids = list(User.objects.filter(username=data["recipient"]).values_list("pk", flat=True))
        else:
            ids = list(User.objects.filter(role=User.Role.CUSTOMER, is_active=True).values_list("pk", flat=True))
        docs = [build_notification(uid, data["title"], data["message"], data["category"]) for uid in ids]
        if docs:
            col(NOTIFICATIONS).insert_many(docs)
        messages.success(request, f"Sent to {len(docs)} user(s).")
        return redirect("notifications:list")
    return render_form(request, form, "Broadcast notification", submit_label="Send",
                       back_url=reverse("notifications:list"))
