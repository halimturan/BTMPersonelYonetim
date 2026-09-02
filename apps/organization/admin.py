from django.contrib import admin
from apps.organization.models import CareerLevel, Department, EmploymentType, JobRole, JobTitle, Unit


class ActiveAdminMixin:
    list_filter = ("active",)


@admin.register(Department)
class DepartmentAdmin(ActiveAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "active")
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(Unit)
class UnitAdmin(ActiveAdminMixin, admin.ModelAdmin):
    list_display = ("name", "department", "parent", "code", "active")
    list_filter = ("active", "department",)
    search_fields = ("name", "code", "department__name",)
    autocomplete_fields = ("department", "parent",)


@admin.register(EmploymentType)
class EmploymentTypeAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ("name", "code", "active",)
    search_fields = ("name", "code",)


@admin.register(JobTitle)
class JobTitleAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ("name", "code", "active",)
    search_fields = ("name", "code",)


@admin.register(JobRole)
class JobRoleAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ("name", "code", "department", "active",)
    list_filter = ("active", "department",)
    search_fields = ("name", "code", "department__name",)
    autocomplete_fields = ("department",)


@admin.register(CareerLevel)
class CareerLevelAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ( "order", "name", "code", "active",)
    list_editable = ("name", "active",)
    ordering = ("order",)
    search_fields = ("name", "code",)
