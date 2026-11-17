"""Demo data for development / screenshots. Idempotent: skips users that exist.

Demo logins (local dev only):
  admin / Admin@12345     (bank staff)
  alice / Customer@123    (customer)
  bob   / Customer@123    (customer)
"""
from django.core.management.base import BaseCommand

from banking import services
from banking.models import Account
from users.models import User

DEMO_USERS = [
    {"username": "admin", "email": "admin@digibank.local", "password": "Admin@12345",
     "role": User.Role.ADMIN, "first_name": "Bank", "last_name": "Admin"},
    {"username": "alice", "email": "alice@digibank.local", "password": "Customer@123",
     "role": User.Role.CUSTOMER, "first_name": "Alice", "last_name": "Wong", "deposit": "50000"},
    {"username": "bob", "email": "bob@digibank.local", "password": "Customer@123",
     "role": User.Role.CUSTOMER, "first_name": "Bob", "last_name": "Somchai", "deposit": "12000"},
]


class Command(BaseCommand):
    help = "Create demo admin + customers with funded accounts."

    def handle(self, *args, **options):
        admin = None
        for spec in DEMO_USERS:
            spec = dict(spec)
            password, deposit = spec.pop("password"), spec.pop("deposit", None)
            user, created = User.objects.get_or_create(username=spec["username"], defaults=spec)
            if spec["role"] == User.Role.ADMIN:
                admin = user
            if not created:
                self.stdout.write(f"skip {user.username} (exists)")
                continue
            user.set_password(password)
            if user.role == User.Role.ADMIN:
                user.is_staff = user.is_superuser = True
            user.save()
            if deposit:
                acc = Account.objects.create(user=user, account_type=Account.Type.SAVINGS, nickname="Main savings")
                Account.objects.create(user=user, account_type=Account.Type.CHECKING, nickname="Daily spending")
                services.deposit(actor=admin or user, account_id=acc.pk, amount=deposit, description="Opening deposit")
            self.stdout.write(self.style.SUCCESS(f"created {user.username}"))
