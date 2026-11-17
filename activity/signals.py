from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .services import log_activity


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_activity(user.pk, "LOGIN", username=user.username, request=request)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user:
        log_activity(user.pk, "LOGOUT", username=user.username, request=request)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    log_activity(
        None,
        "LOGIN_FAILED",
        username=credentials.get("username"),
        status="FAILED",
        request=request,
    )
