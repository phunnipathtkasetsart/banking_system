from django.urls import path

from . import views

app_name = "activity"

urlpatterns = [
    path("", views.my_list, name="my_list"),
    path("all/", views.admin_list, name="admin_list"),
    path("<str:log_id>/edit/", views.edit, name="edit"),
    path("<str:log_id>/delete/", views.delete, name="delete"),
]
