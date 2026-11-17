from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class BankUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Bank", {"fields": ("role", "phone", "avatar")}),)
    list_display = ("username", "email", "role", "is_active")
