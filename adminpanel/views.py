"""Bank-staff back office: dashboard + management of users, accounts, transactions."""
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from activity.services import log_activity
from banking import services
from banking.forms import AccountOpenForm, AdminAccountForm, ReverseForm, TellerForm
from banking.models import Account, Transaction
from banking.services import BankingError
from core.decorators import admin_required
from core.mongo import ACTIVITY_LOGS, SUPPORT_TICKETS, col, to_view
from core.utils import render_confirm, render_form
from notifications.services import notify
from users.forms import AdminUserCreateForm, AdminUserEditForm
from users.models import User


# ---------------------------------------------------------------- dashboard

@admin_required
def dashboard(request):
    today = timezone.localdate()
    since_24h = timezone.now() - timedelta(hours=24)
    todays = Transaction.objects.filter(created_at__date=today)
    ctx = {
        # SQL aggregates
        "customers": User.objects.filter(role=User.Role.CUSTOMER).count(),
        "accounts_by_status": dict(Account.objects.values_list("status").annotate(n=Count("id"))),
        "total_deposits": Account.objects.exclude(status=Account.Status.CLOSED).aggregate(s=Sum("balance"))["s"] or 0,
        "txn_today": todays.count(),
        "volume_today": todays.aggregate(s=Sum("amount"))["s"] or 0,
        "txn_by_type": dict(Transaction.objects.values_list("txn_type").annotate(n=Count("id"))),
        "recent_txns": Transaction.objects.prefetch_related("entries__account")[:10],
        # Mongo aggregates
        "open_tickets": col(SUPPORT_TICKETS).count_documents({"status": {"$in": ["OPEN", "IN_PROGRESS"]}}),
        "failed_24h": col(ACTIVITY_LOGS).count_documents({"status": "FAILED", "timestamp": {"$gte": since_24h}}),
        "recent_logs": [to_view(d) for d in col(ACTIVITY_LOGS).find().sort("timestamp", -1).limit(10)],
        "top_actions": list(col(ACTIVITY_LOGS).aggregate([
            {"$match": {"timestamp": {"$gte": since_24h}}},
            {"$group": {"_id": "$action", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}, {"$limit": 8},
            {"$project": {"_id": 0, "action": "$_id", "n": 1}},
        ])),
    }
    return render(request, "adminpanel/dashboard.html", ctx)


# ---------------------------------------------------------------- users (SQL CRUD)

@admin_required
def user_list(request):
    users = User.objects.annotate(n_accounts=Count("accounts")).order_by("-date_joined")
    if q := request.GET.get("q"):
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) |
                             Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if role := request.GET.get("role"):
        users = users.filter(role=role)
    return render(request, "adminpanel/user_list.html", {"users": users, "q": q or "", "role": role or ""})


@admin_required
def user_create(request):
    form = AdminUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_activity(request.user.pk, "ADMIN_USER_CREATE", username=request.user.username, request=request,
                     metadata={"created": user.username, "role": user.role})
        messages.success(request, f"User {user.username} created.")
        return redirect("adminpanel:user_detail", pk=user.pk)
    return render_form(request, form, "Create user", back_url=reverse("adminpanel:user_list"))


@admin_required
def user_detail(request, pk):
    profile = get_object_or_404(User, pk=pk)
    txns = Transaction.objects.filter(entries__account__user=profile).distinct().prefetch_related("entries__account")[:20]
    return render(request, "adminpanel/user_detail.html",
                  {"profile": profile, "accounts": profile.accounts.all(), "transactions": txns})


@admin_required
def user_edit(request, pk):
    profile = get_object_or_404(User, pk=pk)
    form = AdminUserEditForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request.user.pk, "ADMIN_USER_UPDATE", username=request.user.username, request=request,
                     metadata={"target": profile.username, "changed": form.changed_data})
        messages.success(request, "User updated.")
        return redirect("adminpanel:user_detail", pk=pk)
    return render_form(request, form, f"Edit user {profile.username}",
                       back_url=reverse("adminpanel:user_detail", args=[pk]))


@admin_required
@require_POST
def user_toggle_active(request, pk):
    profile = get_object_or_404(User, pk=pk)
    if profile == request.user:
        messages.error(request, "You cannot deactivate yourself.")
    else:
        profile.is_active = not profile.is_active
        profile.save(update_fields=["is_active"])
        log_activity(request.user.pk, "ADMIN_USER_TOGGLE", username=request.user.username, request=request,
                     metadata={"target": profile.username, "is_active": profile.is_active})
        messages.success(request, f"{profile.username} is now {'active' if profile.is_active else 'inactive'}.")
    return redirect("adminpanel:user_detail", pk=pk)


@admin_required
def user_delete(request, pk):
    profile = get_object_or_404(User, pk=pk)
    back = reverse("adminpanel:user_detail", args=[pk])
    if request.method == "POST":
        if profile == request.user:
            messages.error(request, "You cannot delete yourself.")
            return redirect(back)
        try:
            username = profile.username
            profile.delete()
        except ProtectedError:
            messages.error(request, "User has accounts with transaction history (protected by FK). Deactivate instead.")
            return redirect(back)
        log_activity(request.user.pk, "ADMIN_USER_DELETE", username=request.user.username, request=request,
                     metadata={"deleted": username})
        messages.success(request, f"User {username} deleted.")
        return redirect("adminpanel:user_list")
    return render_confirm(request, f"Delete user {profile.username}?",
                          "Only possible if none of their accounts have transaction history.",
                          back_url=back, submit_label="Delete")


# ---------------------------------------------------------------- accounts (SQL CRUD)

@admin_required
def account_list(request):
    accounts = Account.objects.select_related("user")
    if q := request.GET.get("q"):
        accounts = accounts.filter(Q(account_number__icontains=q) | Q(user__username__icontains=q))
    if status := request.GET.get("status"):
        accounts = accounts.filter(status=status)
    return render(request, "adminpanel/account_list.html",
                  {"accounts": accounts, "q": q or "", "status": status or "", "statuses": Account.Status.choices})


@admin_required
def account_create(request, user_pk):
    owner = get_object_or_404(User, pk=user_pk)
    form = AccountOpenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = services.open_account(user=owner, actor=request.user, request=request, **form.cleaned_data)
        messages.success(request, f"Account {account.account_number} opened for {owner.username}.")
        return redirect("adminpanel:account_detail", pk=account.pk)
    return render_form(request, form, f"Open account for {owner.username}",
                       back_url=reverse("adminpanel:user_detail", args=[user_pk]))


@admin_required
def account_detail(request, pk):
    account = get_object_or_404(Account.objects.select_related("user"), pk=pk)
    teller = TellerForm(request.POST or None)
    if request.method == "POST" and teller.is_valid():
        d = teller.cleaned_data
        fn = services.deposit if d["operation"] == "deposit" else services.withdraw
        try:
            txn = fn(actor=request.user, account_id=pk, amount=d["amount"],
                     description=d["description"] or f"Teller {d['operation']}", request=request)
        except BankingError as exc:
            messages.error(request, f"Failed (rolled back): {exc}")
        else:
            messages.success(request, f"{d['operation'].title()} OK. Ref {txn.reference}.")
        return redirect("adminpanel:account_detail", pk=pk)
    entries = account.entries.select_related("transaction")[:100]
    return render(request, "adminpanel/account_detail.html", {"account": account, "entries": entries, "teller": teller})


@admin_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    old_status = account.status
    form = AdminAccountForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request.user.pk, "ADMIN_ACCOUNT_UPDATE", username=request.user.username, request=request,
                     metadata={"account_number": account.account_number, "changed": form.changed_data,
                               "status": f"{old_status} -> {account.status}"})
        if old_status != account.status:
            notify(account.user_id, "Account status changed",
                   f"Account {account.account_number} is now {account.get_status_display()}.", "SECURITY")
        messages.success(request, "Account updated.")
        return redirect("adminpanel:account_detail", pk=pk)
    return render_form(request, form, f"Edit account {account.account_number}",
                       back_url=reverse("adminpanel:account_detail", args=[pk]))


@admin_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    back = reverse("adminpanel:account_detail", args=[pk])
    if request.method == "POST":
        try:
            result = services.close_account(actor=request.user, account_id=pk, request=request)
        except BankingError as exc:
            messages.error(request, str(exc))
            return redirect(back)
        messages.success(request, f"Account {account.account_number} {result}.")
        return redirect("adminpanel:account_list")
    return render_confirm(request, f"Close/delete account {account.account_number}?",
                          "Balance must be 0. Accounts with history are marked CLOSED; empty ones are deleted.",
                          back_url=back, submit_label="Close / delete")


# ---------------------------------------------------------------- transactions

@admin_required
def transaction_list(request):
    txns = Transaction.objects.prefetch_related("entries__account")
    if q := request.GET.get("q"):
        txns = txns.filter(Q(reference__icontains=q) | Q(entries__account__account_number=q)).distinct()
    if t := request.GET.get("type"):
        txns = txns.filter(txn_type=t)
    if s := request.GET.get("status"):
        txns = txns.filter(status=s)
    return render(request, "adminpanel/transaction_list.html", {
        "transactions": txns[:300], "q": q or "", "type": t or "", "status": s or "",
        "types": Transaction.Type.choices, "statuses": Transaction.Status.choices,
    })


@admin_required
def transaction_detail(request, pk):
    txn = get_object_or_404(Transaction.objects.prefetch_related("entries__account"), pk=pk)
    return render(request, "adminpanel/transaction_detail.html", {"txn": txn})


@admin_required
def transaction_reverse(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    form = ReverseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            rev = services.reverse_transaction(actor=request.user, txn_id=pk,
                                               reason=form.cleaned_data["reason"], request=request)
        except BankingError as exc:
            messages.error(request, f"Reversal failed (rolled back): {exc}")
            return redirect("adminpanel:transaction_detail", pk=pk)
        messages.success(request, f"Reversed. New reference {rev.reference}.")
        return redirect("adminpanel:transaction_detail", pk=rev.pk)
    return render_form(request, form, f"Reverse {txn.reference} ({txn.amount} THB)", submit_label="Reverse",
                       intro="Posts opposite ledger entries in one atomic SQL transaction.",
                       back_url=reverse("adminpanel:transaction_detail", args=[pk]))


@admin_required
def transaction_delete(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    back = reverse("adminpanel:transaction_detail", args=[pk])
    if txn.status != Transaction.Status.REVERSED:
        messages.error(request, "Only REVERSED transactions can be deleted (balances must stay consistent).")
        return redirect(back)
    if request.method == "POST":
        ref = txn.reference
        txn.delete()
        log_activity(request.user.pk, "ADMIN_TXN_DELETE", username=request.user.username, request=request,
                     metadata={"reference": ref})
        messages.success(request, f"Transaction {ref} deleted.")
        return redirect("adminpanel:transaction_list")
    return render_confirm(request, f"Delete {txn.reference}?",
                          "Removes the reversed transaction record and its ledger lines.",
                          back_url=back, submit_label="Delete")
