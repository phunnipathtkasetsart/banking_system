import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


def generate_account_number():
    while True:
        number = "".join(secrets.choice("0123456789") for _ in range(10))
        if not Account.objects.filter(account_number=number).exists():
            return number


def generate_reference():
    return f"TXN{timezone.now():%y%m%d}{secrets.token_hex(4).upper()}"


class Account(models.Model):
    """SQL table `banking_account` — a customer's bank account holding a balance."""

    class Type(models.TextChoices):
        SAVINGS = "SAVINGS", "Savings"
        CHECKING = "CHECKING", "Checking"
        FIXED = "FIXED", "Fixed deposit"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FROZEN = "FROZEN", "Frozen"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts")
    account_number = models.CharField(max_length=10, unique=True, default=generate_account_number, editable=False)
    account_type = models.CharField(max_length=10, choices=Type.choices, default=Type.SAVINGS)
    nickname = models.CharField(max_length=50, blank=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            # DB-level guard: a balance can never go negative, even if app logic has a bug.
            models.CheckConstraint(condition=Q(balance__gte=0), name="account_balance_non_negative"),
        ]

    def __str__(self):
        label = self.nickname or self.get_account_type_display()
        return f"{self.account_number} · {label} · {self.balance} THB"


class Transaction(models.Model):
    """SQL table `banking_transaction` — header of a money movement."""

    class Type(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
        TRANSFER = "TRANSFER", "Transfer"
        REVERSAL = "REVERSAL", "Reversal"

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        REVERSED = "REVERSED", "Reversed"

    reference = models.CharField(max_length=20, unique=True, default=generate_reference, editable=False)
    txn_type = models.CharField(max_length=10, choices=Type.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.COMPLETED)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="initiated_transactions"
    )
    reversal_of = models.OneToOneField(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reversed_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="transaction_amount_positive")]

    def __str__(self):
        return f"{self.reference} {self.txn_type} {self.amount}"


class TransactionEntry(models.Model):
    """SQL table `banking_transactionentry` — double-entry ledger lines.

    A transfer = 1 DEBIT line (sender) + 1 CREDIT line (receiver).
    Junction between Transaction and Account (like Order_Items in the spec).
    """

    class Direction(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="entries")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="entries")
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "transaction entries"

    def __str__(self):
        return f"{self.direction} {self.amount} on {self.account.account_number}"


class Beneficiary(models.Model):
    """SQL table `banking_beneficiary` — saved payees of a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="beneficiaries")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="beneficiary_of")
    nickname = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nickname"]
        verbose_name_plural = "beneficiaries"
        constraints = [models.UniqueConstraint(fields=["user", "account"], name="unique_beneficiary_per_user")]

    def __str__(self):
        return f"{self.nickname} ({self.account.account_number})"
