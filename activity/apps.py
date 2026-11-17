from django.apps import AppConfig


class ActivityConfig(AppConfig):
    name = "activity"

    def ready(self):
        from . import signals  # noqa: F401  (registers login/logout receivers)
