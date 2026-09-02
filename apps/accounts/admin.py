from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        (
            "Personel Bağlantısı",
            {
                "fields": (
                    "employee",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Personel Bağlantısı",
            {
                "fields": (
                    "employee",
                    "email",
                )
            },
        ),
    )

    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "employee",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "employee__personnel_no",
        "employee__first_name",
        "employee__last_name",
    )

    autocomplete_fields = (
        "employee",
    )
