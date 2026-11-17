"""Mongo `activity_logs` CRUD.

Create: automatic (login, transfers, failures...).
Read:   customer sees own; admin sees all with filters.
Update: admin marks a log reviewed + adds a note.
Delete: admin.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.decorators import admin_required
from core.mongo import ACTIVITY_LOGS, col, oid, to_view
from core.utils import render_confirm, render_form


@login_required
def my_list(request):
    logs = [to_view(d) for d in col(ACTIVITY_LOGS).find({"userId": request.user.pk}).sort("timestamp", -1).limit(100)]
    return render(request, "activity/list.html", {"logs": logs, "admin_mode": False})


@admin_required
def admin_list(request):
    q = {}
    for field in ("action", "status", "username"):
        if request.GET.get(field):
            q[field] = request.GET[field]
    if request.GET.get("unreviewed"):
        q["reviewed"] = False
    logs = [to_view(d) for d in col(ACTIVITY_LOGS).find(q).sort("timestamp", -1).limit(300)]
    actions = sorted(a for a in col(ACTIVITY_LOGS).distinct("action") if a)
    return render(request, "activity/list.html",
                  {"logs": logs, "admin_mode": True, "actions": actions, "filters": request.GET})


class ReviewForm(forms.Form):
    reviewed = forms.BooleanField(required=False)
    admin_note = forms.CharField(required=False, widget=forms.Textarea)


@admin_required
def edit(request, log_id):
    doc = col(ACTIVITY_LOGS).find_one({"_id": oid(log_id)})
    if doc is None:
        messages.error(request, "Log not found.")
        return redirect("activity:admin_list")
    form = ReviewForm(request.POST or None, initial={"reviewed": doc.get("reviewed"), "admin_note": doc.get("admin_note")})
    if request.method == "POST" and form.is_valid():
        col(ACTIVITY_LOGS).update_one({"_id": doc["_id"]}, {"$set": {
            **form.cleaned_data, "reviewedBy": request.user.username, "reviewedAt": timezone.now(),
        }})
        messages.success(request, "Log updated.")
        return redirect("activity:admin_list")
    return render_form(request, form, f"Review log: {doc['action']} ({doc.get('status')})",
                       intro=f"user={doc.get('username')} ip={doc.get('ip_address')} metadata={doc.get('metadata')}",
                       back_url=reverse("activity:admin_list"))


@admin_required
def delete(request, log_id):
    _id = oid(log_id)
    if request.method == "POST":
        col(ACTIVITY_LOGS).delete_one({"_id": _id})
        messages.success(request, "Log deleted.")
        return redirect("activity:admin_list")
    return render_confirm(request, "Delete this log entry?", log_id,
                          back_url=reverse("activity:admin_list"), submit_label="Delete")
