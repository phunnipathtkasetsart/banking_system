"""Money-movement services.

Every operation follows the same 2-phase pattern required by the spec:

  Phase 1 — SQL ACID transaction (PostgreSQL)
      `with transaction.atomic():` + `SELECT ... FOR UPDATE` row locks.
      Any exception inside the block => Postgres ROLLBACK, nothing is persisted.

  Phase 2 — Cross-database sync (MongoDB multi-document transaction)
      Only after the SQL commit succeeds: write activity log(s), notification(s),
      and remove the transfer draft (if any) — all-or-nothing inside one Mongo txn.

Failures are logged to Mongo `activity_logs` with status=FAILED so the
rollback scenario is visible in the UI.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction as db_tx

from activity.services import build_log, log_activity
from core.mongo import ACTIVITY_LOGS, NOTIFICATIONS, TRANSFER_DRAFTS, col, run_mongo_transaction
from notifications.services import build_notification

from .models import Account, Transaction, TransactionEntry

logger = logging.getLogger(__name__)


class BankingError(Exception):
    """Business-rule violation. Raising it inside atomic() triggers rollback."""


# ---------------------------------------------------------------- helpers

def _amount(value) -> Decimal:
    try:
        amt = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise BankingError("Invalid amount.")
    if amt <= 0:
        raise BankingError("Amount must be greater than zero.")
    return amt


def _require_active(account):
    if account.status != Account.Status.ACTIVE:
        raise BankingError(f"Account {account.account_number} is {account.get_status_display().lower()}.")


def _require_owner(actor, account):
    if not actor.is_bank_admin and account.user_id != actor.pk:
        raise BankingError("You do not own this account.")


def _fail(actor, action, reason, request, metadata):
    log_activity(
        actor.pk, action, username=actor.username, status="FAILED", request=request,
        metadata={**metadata, "reason": str(reason), "rolled_back": True},
    )


def sync_to_mongo(*, logs=(), notifications=(), delete_draft=None):
    """Phase 2: one Mongo multi-document transaction for all NoSQL side effects."""

    def work(session):
        if logs:
            col(ACTIVITY_LOGS).insert_many(list(logs), session=session)
        if notifications:
            col(NOTIFICATIONS).insert_many(list(notifications), session=session)
        if delete_draft:
            col(TRANSFER_DRAFTS).delete_one(delete_draft, session=session)

    try:
        run_mongo_transaction(work)
    except Exception:
        # SQL already committed — money is safe; only the side effects are lost.
        logger.exception("Mongo sync failed after SQL commit")


# ---------------------------------------------------------------- accounts

def open_account(*, user, account_type, nickname="", request=None, actor=None):
    actor = actor or user
    account = Account.objects.create(user=user, account_type=account_type, nickname=nickname)
    sync_to_mongo(
        logs=[build_log(actor.pk, "ACCOUNT_OPEN", username=actor.username, request=request,
                        metadata={"account_number": account.account_number, "owner_id": user.pk})],
        notifications=[build_notification(user.pk, "New account opened",
                                          f"Account {account.account_number} ({account.get_account_type_display()}) is ready.")],
    )
    return account


def close_account(*, actor, account_id, request=None):
    """Delete the row if it has no history, otherwise mark it CLOSED. Balance must be 0."""
    with db_tx.atomic():
        account = Account.objects.select_for_update().get(pk=account_id)
        _require_owner(actor, account)
        if account.balance != 0:
            raise BankingError("Move the remaining balance out before closing this account.")
        number = account.account_number
        if account.entries.exists():
            account.status = Account.Status.CLOSED
            account.save(update_fields=["status", "updated_at"])
            result = "closed"
        else:
            account.delete()
            result = "deleted"
    log_activity(actor.pk, "ACCOUNT_CLOSE", username=actor.username, request=request,
                 metadata={"account_number": number, "result": result})
    return result


# ---------------------------------------------------------------- money

def deposit(*, actor, account_id, amount, description="", request=None):
    meta = {"account_id": account_id, "amount": str(amount)}
    try:
        amt = _amount(amount)
        with db_tx.atomic():
            acc = Account.objects.select_for_update().get(pk=account_id)
            _require_owner(actor, acc)
            _require_active(acc)
            acc.balance += amt
            acc.save(update_fields=["balance", "updated_at"])
            txn = Transaction.objects.create(
                txn_type=Transaction.Type.DEPOSIT, amount=amt, description=description, created_by=actor
            )
            TransactionEntry.objects.create(
                transaction=txn, account=acc, direction=TransactionEntry.Direction.CREDIT,
                amount=amt, balance_after=acc.balance,
            )
    except Account.DoesNotExist:
        _fail(actor, "DEPOSIT", "Account not found", request, meta)
        raise BankingError("Account not found.")
    except BankingError as exc:
        _fail(actor, "DEPOSIT", exc, request, meta)
        raise

    sync_to_mongo(
        logs=[build_log(actor.pk, "DEPOSIT", username=actor.username, request=request,
                        metadata={"reference": txn.reference, "account_number": acc.account_number, "amount": str(amt)})],
        notifications=[build_notification(acc.user_id, "Deposit received",
                                          f"{amt} THB deposited to {acc.account_number}. Balance: {acc.balance} THB.",
                                          "TRANSACTION")],
    )
    return txn


def withdraw(*, actor, account_id, amount, description="", request=None):
    meta = {"account_id": account_id, "amount": str(amount)}
    try:
        amt = _amount(amount)
        with db_tx.atomic():
            acc = Account.objects.select_for_update().get(pk=account_id)
            _require_owner(actor, acc)
            _require_active(acc)
            if acc.balance < amt:
                raise BankingError("Insufficient funds.")
            acc.balance -= amt
            acc.save(update_fields=["balance", "updated_at"])
            txn = Transaction.objects.create(
                txn_type=Transaction.Type.WITHDRAWAL, amount=amt, description=description, created_by=actor
            )
            TransactionEntry.objects.create(
                transaction=txn, account=acc, direction=TransactionEntry.Direction.DEBIT,
                amount=amt, balance_after=acc.balance,
            )
    except Account.DoesNotExist:
        _fail(actor, "WITHDRAWAL", "Account not found", request, meta)
        raise BankingError("Account not found.")
    except IntegrityError:
        _fail(actor, "WITHDRAWAL", "DB constraint violated (negative balance)", request, meta)
        raise BankingError("Insufficient funds.")
    except BankingError as exc:
        _fail(actor, "WITHDRAWAL", exc, request, meta)
        raise

    sync_to_mongo(
        logs=[build_log(actor.pk, "WITHDRAWAL", username=actor.username, request=request,
                        metadata={"reference": txn.reference, "account_number": acc.account_number, "amount": str(amt)})],
        notifications=[build_notification(acc.user_id, "Withdrawal",
                                          f"{amt} THB withdrawn from {acc.account_number}. Balance: {acc.balance} THB.",
                                          "TRANSACTION")],
    )
    return txn


def transfer(*, actor, from_account_id, to_account_number, amount, description="",
             simulate_failure=False, request=None, draft_id=None):
    """Atomic transfer between two accounts.

    Steps (single Postgres transaction):
      1. lock both account rows (ordered by pk to avoid deadlocks)
      2. validate ownership, status, balance
      3. debit sender, credit receiver
      4. insert Transaction header + 2 TransactionEntry rows
      (5. optional simulated crash -> proves full rollback)
    Then: Mongo txn -> activity log, 2 notifications, delete draft.
    """
    meta = {"from_account_id": from_account_id, "to_account_number": to_account_number,
            "amount": str(amount), "simulate_failure": simulate_failure}
    try:
        amt = _amount(amount)
        from_account_id = int(from_account_id)
        with db_tx.atomic():
            dst_id = Account.objects.filter(account_number=to_account_number).values_list("pk", flat=True).first()
            if dst_id is None:
                raise BankingError("Destination account not found.")
            if dst_id == from_account_id:
                raise BankingError("Cannot transfer to the same account.")

            locked = {
                a.pk: a
                for a in Account.objects.select_for_update().filter(pk__in=[from_account_id, dst_id]).order_by("pk")
            }
            src, dst = locked.get(from_account_id), locked[dst_id]
            if src is None:
                raise BankingError("Source account not found.")
            _require_owner(actor, src)
            _require_active(src)
            _require_active(dst)
            if src.balance < amt:
                raise BankingError("Insufficient funds.")

            src.balance -= amt
            src.save(update_fields=["balance", "updated_at"])
            dst.balance += amt
            dst.save(update_fields=["balance", "updated_at"])

            txn = Transaction.objects.create(
                txn_type=Transaction.Type.TRANSFER, amount=amt, description=description, created_by=actor
            )
            TransactionEntry.objects.bulk_create([
                TransactionEntry(transaction=txn, account=src, direction=TransactionEntry.Direction.DEBIT,
                                 amount=amt, balance_after=src.balance),
                TransactionEntry(transaction=txn, account=dst, direction=TransactionEntry.Direction.CREDIT,
                                 amount=amt, balance_after=dst.balance),
            ])

            if simulate_failure:
                # Everything above (debit, credit, header, entries) is undone by ROLLBACK.
                raise BankingError("Simulated system failure after debit/credit — transaction rolled back.")
    except IntegrityError:
        _fail(actor, "TRANSFER", "DB constraint violated", request, meta)
        raise BankingError("Transfer rejected by database constraints.")
    except BankingError as exc:
        _fail(actor, "TRANSFER", exc, request, meta)
        raise

    draft_filter = {"_id": draft_id, "userId": actor.pk} if draft_id else None
    sync_to_mongo(
        logs=[build_log(actor.pk, "TRANSFER", username=actor.username, request=request,
                        metadata={"reference": txn.reference, "from": src.account_number,
                                  "to": dst.account_number, "amount": str(amt)})],
        notifications=[
            build_notification(src.user_id, "Transfer sent",
                               f"{amt} THB sent from {src.account_number} to {dst.account_number}. Ref {txn.reference}.",
                               "TRANSACTION"),
            build_notification(dst.user_id, "Money received",
                               f"{amt} THB received on {dst.account_number} from {src.account_number}. Ref {txn.reference}.",
                               "TRANSACTION"),
        ],
        delete_draft=draft_filter,
    )
    return txn


def reverse_transaction(*, actor, txn_id, reason="", request=None):
    """Admin: undo a completed transaction by posting opposite ledger entries."""
    meta = {"txn_id": txn_id, "reason": reason}
    try:
        with db_tx.atomic():
            txn = Transaction.objects.select_for_update().get(pk=txn_id)
            if txn.status != Transaction.Status.COMPLETED or txn.txn_type == Transaction.Type.REVERSAL:
                raise BankingError("Only completed, non-reversal transactions can be reversed.")
            entries = list(txn.entries.all())
            accounts = {
                a.pk: a
                for a in Account.objects.select_for_update()
                .filter(pk__in=[e.account_id for e in entries]).order_by("pk")
            }
            reversal = Transaction.objects.create(
                txn_type=Transaction.Type.REVERSAL, amount=txn.amount, created_by=actor, reversal_of=txn,
                description=f"Reversal of {txn.reference}" + (f": {reason}" if reason else ""),
            )
            new_entries = []
            for e in entries:
                acc = accounts[e.account_id]
                if e.direction == TransactionEntry.Direction.CREDIT:
                    if acc.balance < e.amount:
                        raise BankingError(f"Account {acc.account_number} lacks funds to reverse.")
                    acc.balance -= e.amount
                    direction = TransactionEntry.Direction.DEBIT
                else:
                    acc.balance += e.amount
                    direction = TransactionEntry.Direction.CREDIT
                acc.save(update_fields=["balance", "updated_at"])
                new_entries.append(TransactionEntry(transaction=reversal, account=acc, direction=direction,
                                                    amount=e.amount, balance_after=acc.balance))
            TransactionEntry.objects.bulk_create(new_entries)
            txn.status = Transaction.Status.REVERSED
            txn.save(update_fields=["status"])
    except Transaction.DoesNotExist:
        raise BankingError("Transaction not found.")
    except BankingError as exc:
        _fail(actor, "REVERSAL", exc, request, meta)
        raise

    sync_to_mongo(
        logs=[build_log(actor.pk, "REVERSAL", username=actor.username, request=request,
                        metadata={"original": txn.reference, "reversal": reversal.reference, "reason": reason})],
        notifications=[
            build_notification(acc.user_id, "Transaction reversed",
                               f"{txn.reference} was reversed by the bank. Account {acc.account_number} balance: {acc.balance} THB.",
                               "TRANSACTION")
            for acc in accounts.values()
        ],
    )
    return reversal
