from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
    )

    employee = models.OneToOneField(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_account",
    )

    def __str__(self):
        return self.get_full_name() or self.username
