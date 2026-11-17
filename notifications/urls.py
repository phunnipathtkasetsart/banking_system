from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("read-all/", views.mark_all_read, name="mark_all_read"),
    path("clear/", views.clear_all, name="clear_all"),
    path("broadcast/", views.broadcast, name="broadcast"),
    path("<str:notification_id>/read/", views.mark_read, name="mark_read"),
    path("<str:notification_id>/delete/", views.delete, name="delete"),
]
