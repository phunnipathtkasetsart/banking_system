from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("new/", views.ticket_create, name="ticket_create"),
    path("<str:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("<str:ticket_id>/edit/", views.ticket_edit, name="ticket_edit"),
    path("<str:ticket_id>/status/", views.ticket_status, name="ticket_status"),
    path("<str:ticket_id>/delete/", views.ticket_delete, name="ticket_delete"),
]
