from django.urls import path

from . import views

app_name = "banking"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # accounts
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/open/", views.account_open, name="account_open"),
    path("accounts/<int:pk>/", views.account_detail, name="account_detail"),
    path("accounts/<int:pk>/edit/", views.account_edit, name="account_edit"),
    path("accounts/<int:pk>/close/", views.account_close, name="account_close"),
    # money
    path("deposit/", views.deposit, name="deposit"),
    path("withdraw/", views.withdraw, name="withdraw"),
    path("transfer/", views.transfer, name="transfer"),
    # transactions
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    # beneficiaries
    path("beneficiaries/", views.beneficiary_list, name="beneficiary_list"),
    path("beneficiaries/add/", views.beneficiary_create, name="beneficiary_create"),
    path("beneficiaries/<int:pk>/edit/", views.beneficiary_edit, name="beneficiary_edit"),
    path("beneficiaries/<int:pk>/delete/", views.beneficiary_delete, name="beneficiary_delete"),
    # transfer drafts (Mongo)
    path("drafts/", views.draft_list, name="draft_list"),
    path("drafts/new/", views.draft_create, name="draft_create"),
    path("drafts/<str:draft_id>/edit/", views.draft_edit, name="draft_edit"),
    path("drafts/<str:draft_id>/delete/", views.draft_delete, name="draft_delete"),
    path("drafts/<str:draft_id>/execute/", views.draft_execute, name="draft_execute"),
]
