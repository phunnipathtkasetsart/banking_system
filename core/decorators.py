from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def admin_required(view):
    """Only bank staff (role=ADMIN or superuser)."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_bank_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def customer_required(view):
    """Only customers; admins get bounced to their dashboard."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_bank_admin:
            return redirect("adminpanel:dashboard")
        return view(request, *args, **kwargs)

    return wrapper
