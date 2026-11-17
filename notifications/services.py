"""Mongo collection `notifications` — in-app alerts.

Document shape:
{ _id, userId, title, message, category: INFO|TRANSACTION|SECURITY|BROADCAST|SUPPORT,
  isRead: bool, sentAt, readAt }
"""
import logging

from django.utils import timezone
from pymongo.errors import PyMongoError

from core.mongo import NOTIFICATIONS, col

logger = logging.getLogger(__name__)


def build_notification(user_id, title, message, category="INFO"):
    return {
        "userId": user_id,
        "title": title,
        "message": message,
        "category": category,
        "isRead": False,
        "sentAt": timezone.now(),
        "readAt": None,
    }


def notify(user_id, title, message, category="INFO"):
    try:
        col(NOTIFICATIONS).insert_one(build_notification(user_id, title, message, category))
    except PyMongoError:
        logger.exception("Failed to write notification")


def unread_count(user_id):
    return col(NOTIFICATIONS).count_documents({"userId": user_id, "isRead": False})
