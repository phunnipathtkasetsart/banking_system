from pymongo.errors import PyMongoError

from .services import unread_count


def unread_notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or user.is_bank_admin:
        return {}
    try:
        return {"unread_notifications": unread_count(user.pk)}
    except PyMongoError:
        return {}
