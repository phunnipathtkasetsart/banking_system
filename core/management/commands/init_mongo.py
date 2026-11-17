from django.core.management.base import BaseCommand

from core.mongo import ALL_COLLECTIONS, ensure_collections_and_indexes


class Command(BaseCommand):
    help = "Create MongoDB collections and indexes (idempotent)."

    def handle(self, *args, **options):
        ensure_collections_and_indexes()
        self.stdout.write(self.style.SUCCESS(f"Mongo ready: {', '.join(ALL_COLLECTIONS)}"))
