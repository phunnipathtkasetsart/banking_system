"""Mongo collection `activity_logs` — audit trail.

Document shape:
{ _id, userId, username, action, status: SUCCESS|FAILED, ip_address, user_agent,
  metadata: {...free-form...}, reviewed: bool, admin_note: str, timestamp }
"""
import logging

from django.utils import timezone
from pymongo.errors import PyMongoError

from core.mongo import ACTIVITY_LOGS, col
from core.utils import client_ip

logger = logging.getLogger(__name__)


def build_log(user_id, action, *, username=None, status="SUCCESS", request=None, metadata=None):
    return {
        "userId": user_id,
        "username": username,
        "action": action,
        "status": status,
        "ip_address": client_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT", "") if request else "",
        "metadata": metadata or {},
        "reviewed": False,
        "admin_note": "",
        "timestamp": timezone.now(),
    }


def log_activity(user_id, action, **kwargs):
    """Fire-and-forget log write. Never breaks the request if Mongo is down."""
    try:
        col(ACTIVITY_LOGS).insert_one(build_log(user_id, action, **kwargs))
    except PyMongoError:
        logger.exception("Failed to write activity log %s", action)
