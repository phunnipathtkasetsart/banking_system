from django.db import transaction as db_tx

from activity.services import build_log
from banking.models import Account
from banking.services import sync_to_mongo
from notifications.services import build_notification


def register_customer(form, request=None):
    """SQL txn: create user + default savings account (both or neither).
    Then Mongo txn: REGISTER log + welcome notification."""
    with db_tx.atomic():
        user = form.save()
        account = Account.objects.create(user=user, account_type=Account.Type.SAVINGS, nickname="Main savings")

    sync_to_mongo(
        logs=[build_log(user.pk, "REGISTER", username=user.username, request=request,
                        metadata={"account_number": account.account_number})],
        notifications=[build_notification(user.pk, "Welcome to DigiBank",
                                          f"Your savings account {account.account_number} is ready.")],
    )
    return user
