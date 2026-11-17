from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """SQL table `users_user` — customers and bank staff."""

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)  # stored on local disk (MEDIA_ROOT)

    @property
    def is_bank_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self):
        return self.username
