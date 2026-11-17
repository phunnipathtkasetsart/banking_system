"""MongoDB access layer (NoSQL side of the hybrid architecture).

Every app talks to Mongo through these helpers so the connection, collection
names and indexes live in one place.
"""
from functools import lru_cache

from bson import ObjectId
from bson.errors import InvalidId
from django.conf import settings
from django.http import Http404
from pymongo import ASCENDING, DESCENDING, MongoClient

# Collection names
ACTIVITY_LOGS = "activity_logs"
NOTIFICATIONS = "notifications"
SUPPORT_TICKETS = "support_tickets"
TRANSFER_DRAFTS = "transfer_drafts"

ALL_COLLECTIONS = [ACTIVITY_LOGS, NOTIFICATIONS, SUPPORT_TICKETS, TRANSFER_DRAFTS]


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(settings.MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=5000)


def get_db():
    return get_client()[settings.MONGO_DB_NAME]


def col(name):
    return get_db()[name]


def oid(value) -> ObjectId:
    """Parse an ObjectId from a URL segment, 404 on garbage."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise Http404("Invalid id")


def to_view(doc):
    """Templates can't read `_id` (leading underscore), so expose it as `id`."""
    if doc is None:
        return None
    doc["id"] = str(doc["_id"])
    return doc


def run_mongo_transaction(fn):
    """Run fn(session) inside a MongoDB multi-document transaction.

    Commits if fn returns, aborts (rolls back) if it raises.
    """
    with get_client().start_session() as session:
        return session.with_transaction(fn)


def ensure_collections_and_indexes():
    db = get_db()
    existing = set(db.list_collection_names())
    for name in ALL_COLLECTIONS:
        if name not in existing:
            db.create_collection(name)

    db[ACTIVITY_LOGS].create_index([("userId", ASCENDING), ("timestamp", DESCENDING)])
    db[ACTIVITY_LOGS].create_index([("action", ASCENDING)])
    db[NOTIFICATIONS].create_index([("userId", ASCENDING), ("isRead", ASCENDING), ("sentAt", DESCENDING)])
    db[SUPPORT_TICKETS].create_index([("userId", ASCENDING), ("status", ASCENDING)])
    db[TRANSFER_DRAFTS].create_index([("userId", ASCENDING), ("updatedAt", DESCENDING)])
