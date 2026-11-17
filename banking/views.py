"""Customer-facing banking views."""
from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from activity.services import log_activity
from core.decorators import customer_required
from core.mongo import TRANSFER_DRAFTS, col, oid, to_view
from core.utils import render_confirm, render_form

from . import services
from .forms import (
    AccountEditForm, AccountOpenForm, BeneficiaryCreateForm, BeneficiaryEditForm,
    DraftForm, MoneyForm, TransferForm,
)
from .models import Account, Beneficiary, Transaction
from .services import BankingError


def customer_transactions(user):
    return (
        Transaction.objects.filter(entries__account__user=user)
        .distinct()
        .prefetch_related("entries__account")
    )


# ---------------------------------------------------------------- dashboard

@customer_required
def dashboard(request):
    accounts = request.user.accounts.exclude(status=Account.Status.CLOSED)
    return render(request, "banking/dashboard.html", {
        "accounts": accounts,
        "total": accounts.aggregate(s=Sum("balance"))["s"] or 0,
        "recent": customer_transactions(request.user)[:5],
        "draft_count": col(TRANSFER_DRAFTS).count_documents({"userId": request.user.pk}),
    })


# ---------------------------------------------------------------- accounts (SQL CRUD)

@customer_required
def account_list(request):
    return render(request, "banking/account_list.html", {"accounts": request.user.accounts.all()})


@customer_required
def account_open(request):
    form = AccountOpenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = services.open_account(user=request.user, request=request, **form.cleaned_data)
        messages.success(request, f"Account {account.account_number} opened.")
        return redirect("banking:account_detail", pk=account.pk)
    return render_form(request, form, "Open a new account", submit_label="Open account",
                       back_url=reverse("banking:account_list"))


@customer_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)
    entries = account.entries.select_related("transaction")[:100]
    return render(request, "banking/account_detail.html", {"account": account, "entries": entries})


@customer_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)
    form = AccountEditForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account updated.")
        return redirect("banking:account_detail", pk=pk)
    return render_form(request, form, f"Edit account {account.account_number}",
                       back_url=reverse("banking:account_detail", args=[pk]))


@customer_required
def account_close(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)
    if request.method == "POST":
        try:
            result = services.close_account(actor=request.user, account_id=pk, request=request)
        except BankingError as exc:
            messages.error(request, str(exc))
            return redirect("banking:account_detail", pk=pk)
        messages.success(request, f"Account {account.account_number} {result}.")
        return redirect("banking:account_list")
    return render_confirm(
        request, f"Close account {account.account_number}?",
        "Balance must be 0. Accounts with history are marked CLOSED; empty ones are deleted.",
        back_url=reverse("banking:account_detail", args=[pk]), submit_label="Close account",
    )


# ---------------------------------------------------------------- money movement

def _money_view(request, op, title):
    form = MoneyForm(request.user, request.POST or None, initial={"account": request.GET.get("account")})
    if request.method == "POST" and form.is_valid():
        fn = services.deposit if op == "deposit" else services.withdraw
        try:
            txn = fn(actor=request.user, account_id=form.cleaned_data["account"].pk,
                     amount=form.cleaned_data["amount"], description=form.cleaned_data["description"],
                     request=request)
        except BankingError as exc:
            messages.error(request, f"{title} failed (rolled back): {exc}")
        else:
            messages.success(request, f"{title} successful. Ref {txn.reference}.")
            return redirect("banking:transaction_detail", pk=txn.pk)
    return render_form(request, form, title, submit_label=title, back_url=reverse("banking:dashboard"))


@customer_required
def deposit(request):
    return _money_view(request, "deposit", "Deposit")


@customer_required
def withdraw(request):
    return _money_view(request, "withdraw", "Withdraw")


@customer_required
def transfer(request):
    form = TransferForm(request.user, request.POST or None,
                        initial={"to_account_number": request.GET.get("to", "")})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if "save_draft" in request.POST:
            _save_draft(request.user, data)
            messages.success(request, "Saved as draft.")
            return redirect("banking:draft_list")
        try:
            txn = services.transfer(
                actor=request.user, from_account_id=data["from_account"].pk,
                to_account_number=data["to_account_number"], amount=data["amount"],
                description=data["description"], simulate_failure=data["simulate_failure"], request=request,
            )
        except BankingError as exc:
            messages.error(request, f"Transfer failed and was rolled back: {exc}")
        else:
            messages.success(request, f"Transfer successful. Ref {txn.reference}.")
            return redirect("banking:transaction_detail", pk=txn.pk)
    beneficiaries = request.user.beneficiaries.select_related("account")
    return render(request, "banking/transfer.html", {"form": form, "beneficiaries": beneficiaries})


# ---------------------------------------------------------------- transactions (read)

@customer_required
def transaction_list(request):
    return render(request, "banking/transaction_list.html",
                  {"transactions": customer_transactions(request.user)[:200]})


@customer_required
def transaction_detail(request, pk):
    txn = get_object_or_404(customer_transactions(request.user), pk=pk)
    return render(request, "banking/transaction_detail.html", {"txn": txn})


# ---------------------------------------------------------------- beneficiaries (SQL CRUD)

@customer_required
def beneficiary_list(request):
    return render(request, "banking/beneficiary_list.html",
                  {"beneficiaries": request.user.beneficiaries.select_related("account__user")})


@customer_required
def beneficiary_create(request):
    form = BeneficiaryCreateForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        Beneficiary.objects.create(user=request.user, account=form.account, nickname=form.cleaned_data["nickname"])
        log_activity(request.user.pk, "BENEFICIARY_ADD", username=request.user.username, request=request,
                     metadata={"account_number": form.account.account_number})
        messages.success(request, "Beneficiary added.")
        return redirect("banking:beneficiary_list")
    return render_form(request, form, "Add beneficiary", back_url=reverse("banking:beneficiary_list"))


@customer_required
def beneficiary_edit(request, pk):
    beneficiary = get_object_or_404(Beneficiary, pk=pk, user=request.user)
    form = BeneficiaryEditForm(request.POST or None, instance=beneficiary)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Beneficiary updated.")
        return redirect("banking:beneficiary_list")
    return render_form(request, form, "Edit beneficiary", back_url=reverse("banking:beneficiary_list"))


@customer_required
def beneficiary_delete(request, pk):
    beneficiary = get_object_or_404(Beneficiary, pk=pk, user=request.user)
    if request.method == "POST":
        beneficiary.delete()
        messages.success(request, "Beneficiary removed.")
        return redirect("banking:beneficiary_list")
    return render_confirm(request, "Remove beneficiary?", str(beneficiary),
                          back_url=reverse("banking:beneficiary_list"), submit_label="Remove")


# ---------------------------------------------------------------- transfer drafts (Mongo CRUD)

def _draft_doc(data):
    return {
        "fromAccountId": data["from_account"].pk,
        "fromAccountNumber": data["from_account"].account_number,
        "toAccountNumber": data["to_account_number"],
        "amount": str(data["amount"].quantize(Decimal("0.01"))),
        "description": data["description"],
        "updatedAt": timezone.now(),
    }


def _save_draft(user, data):
    doc = _draft_doc(data) | {"userId": user.pk, "createdAt": timezone.now()}
    return col(TRANSFER_DRAFTS).insert_one(doc).inserted_id


def _get_draft(request, draft_id):
    doc = col(TRANSFER_DRAFTS).find_one({"_id": oid(draft_id), "userId": request.user.pk})
    if doc is None:
        raise Http404("Draft not found")
    return to_view(doc)


@customer_required
def draft_list(request):
    drafts = [to_view(d) for d in col(TRANSFER_DRAFTS).find({"userId": request.user.pk}).sort("updatedAt", -1)]
    return render(request, "banking/draft_list.html", {"drafts": drafts})


@customer_required
def draft_create(request):
    form = DraftForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        _save_draft(request.user, form.cleaned_data)
        messages.success(request, "Draft saved.")
        return redirect("banking:draft_list")
    return render_form(request, form, "New transfer draft", back_url=reverse("banking:draft_list"))


@customer_required
def draft_edit(request, draft_id):
    draft = _get_draft(request, draft_id)
    initial = {"from_account": draft["fromAccountId"], "to_account_number": draft["toAccountNumber"],
               "amount": draft["amount"], "description": draft.get("description", "")}
    form = DraftForm(request.user, request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        col(TRANSFER_DRAFTS).update_one({"_id": draft["_id"]}, {"$set": _draft_doc(form.cleaned_data)})
        messages.success(request, "Draft updated.")
        return redirect("banking:draft_list")
    return render_form(request, form, "Edit transfer draft", back_url=reverse("banking:draft_list"))


@customer_required
def draft_delete(request, draft_id):
    draft = _get_draft(request, draft_id)
    if request.method == "POST":
        col(TRANSFER_DRAFTS).delete_one({"_id": draft["_id"]})
        messages.success(request, "Draft deleted.")
        return redirect("banking:draft_list")
    return render_confirm(request, "Delete draft?",
                          f"{draft['amount']} THB to {draft['toAccountNumber']}",
                          back_url=reverse("banking:draft_list"), submit_label="Delete")


@customer_required
@require_POST
def draft_execute(request, draft_id):
    """Run the draft as a real transfer. On success the draft is removed in the Mongo sync step."""
    draft = _get_draft(request, draft_id)
    try:
        txn = services.transfer(
            actor=request.user, from_account_id=draft["fromAccountId"],
            to_account_number=draft["toAccountNumber"], amount=draft["amount"],
            description=draft.get("description", ""), request=request, draft_id=draft["_id"],
        )
    except BankingError as exc:
        messages.error(request, f"Transfer failed and was rolled back (draft kept): {exc}")
        return redirect("banking:draft_list")
    messages.success(request, f"Draft sent. Ref {txn.reference}.")
    return redirect("banking:transaction_detail", pk=txn.pk)
