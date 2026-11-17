"""Mongo `support_tickets` CRUD.

Document shape:
{ _id, userId, username, subject, category, priority, status,
  messages: [ {authorId, authorName, isStaff, body, createdAt} ],   <- embedded array
  createdAt, updatedAt }
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.mongo import SUPPORT_TICKETS, col, oid, to_view
from core.utils import render_confirm, render_form
from notifications.services import notify

STATUSES = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
CATEGORIES = ["ACCOUNT", "TRANSFER", "CARD", "SECURITY", "OTHER"]
PRIORITIES = ["LOW", "MEDIUM", "HIGH"]


def _choices(values):
    return [(v, v.replace("_", " ").title()) for v in values]


class TicketForm(forms.Form):
    subject = forms.CharField(max_length=150)
    category = forms.ChoiceField(choices=_choices(CATEGORIES))
    priority = forms.ChoiceField(choices=_choices(PRIORITIES))


class TicketCreateForm(TicketForm):
    message = forms.CharField(widget=forms.Textarea)


class ReplyForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea, label="Reply")


def _get_ticket(request, ticket_id):
    q = {"_id": oid(ticket_id)}
    if not request.user.is_bank_admin:
        q["userId"] = request.user.pk
    doc = col(SUPPORT_TICKETS).find_one(q)
    if doc is None:
        raise Http404("Ticket not found")
    return to_view(doc)


def _message(user, body):
    return {"authorId": user.pk, "authorName": user.username, "isStaff": user.is_bank_admin,
            "body": body, "createdAt": timezone.now()}


@login_required
def ticket_list(request):
    q = {} if request.user.is_bank_admin else {"userId": request.user.pk}
    if request.GET.get("status"):
        q["status"] = request.GET["status"]
    tickets = [to_view(d) for d in col(SUPPORT_TICKETS).find(q, {"messages": 0}).sort("updatedAt", -1)]
    return render(request, "support/list.html", {"tickets": tickets, "statuses": STATUSES})


@login_required
def ticket_create(request):
    if request.user.is_bank_admin:
        raise PermissionDenied
    form = TicketCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        now = timezone.now()
        res = col(SUPPORT_TICKETS).insert_one({
            "userId": request.user.pk, "username": request.user.username,
            "subject": d["subject"], "category": d["category"], "priority": d["priority"],
            "status": "OPEN", "messages": [_message(request.user, d["message"])],
            "createdAt": now, "updatedAt": now,
        })
        messages.success(request, "Ticket created.")
        return redirect("support:ticket_detail", ticket_id=str(res.inserted_id))
    return render_form(request, form, "New support ticket", submit_label="Submit",
                       back_url=reverse("support:ticket_list"))


@login_required
def ticket_detail(request, ticket_id):
    ticket = _get_ticket(request, ticket_id)
    form = ReplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        update = {"$push": {"messages": _message(request.user, form.cleaned_data["body"])},
                  "$set": {"updatedAt": timezone.now()}}
        if request.user.is_bank_admin and ticket["status"] == "OPEN":
            update["$set"]["status"] = "IN_PROGRESS"
        col(SUPPORT_TICKETS).update_one({"_id": ticket["_id"]}, update)
        if request.user.is_bank_admin:
            notify(ticket["userId"], "Support replied", f"New reply on ticket: {ticket['subject']}", "SUPPORT")
        messages.success(request, "Reply posted.")
        return redirect("support:ticket_detail", ticket_id=ticket_id)
    return render(request, "support/detail.html", {"ticket": ticket, "form": form, "statuses": STATUSES})


@login_required
def ticket_edit(request, ticket_id):
    ticket = _get_ticket(request, ticket_id)
    if ticket["status"] == "CLOSED":
        messages.error(request, "Closed tickets cannot be edited.")
        return redirect("support:ticket_detail", ticket_id=ticket_id)
    form = TicketForm(request.POST or None, initial=ticket)
    if request.method == "POST" and form.is_valid():
        col(SUPPORT_TICKETS).update_one({"_id": ticket["_id"]},
                                        {"$set": {**form.cleaned_data, "updatedAt": timezone.now()}})
        messages.success(request, "Ticket updated.")
        return redirect("support:ticket_detail", ticket_id=ticket_id)
    return render_form(request, form, "Edit ticket", back_url=reverse("support:ticket_detail", args=[ticket_id]))


@login_required
@require_POST
def ticket_status(request, ticket_id):
    ticket = _get_ticket(request, ticket_id)
    status = request.POST.get("status")
    # customers may only close their own ticket; staff can set any status
    if status not in STATUSES or (not request.user.is_bank_admin and status != "CLOSED"):
        raise PermissionDenied
    col(SUPPORT_TICKETS).update_one({"_id": ticket["_id"]}, {"$set": {"status": status, "updatedAt": timezone.now()}})
    if request.user.is_bank_admin:
        notify(ticket["userId"], "Ticket status changed", f"'{ticket['subject']}' is now {status}.", "SUPPORT")
    messages.success(request, f"Status set to {status}.")
    return redirect("support:ticket_detail", ticket_id=ticket_id)


@login_required
def ticket_delete(request, ticket_id):
    ticket = _get_ticket(request, ticket_id)
    if request.method == "POST":
        col(SUPPORT_TICKETS).delete_one({"_id": ticket["_id"]})
        messages.success(request, "Ticket deleted.")
        return redirect("support:ticket_list")
    return render_confirm(request, "Delete ticket?", ticket["subject"],
                          back_url=reverse("support:ticket_detail", args=[ticket_id]), submit_label="Delete")
