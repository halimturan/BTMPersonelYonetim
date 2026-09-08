from django.contrib import admin
from apps.organization.models import CareerLevel, Department, EmploymentType, JobRole, JobTitle, Unit, ManagementLevel


class ActiveAdminMixin:
    list_filter = ("active",)


@admin.register(Department)
class DepartmentAdmin(ActiveAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "active")
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(Unit)
class UnitAdmin(ActiveAdminMixin, admin.ModelAdmin):
    list_display = ("name", "department", "code", "active")
    list_filter = ("active", "department",)
    search_fields = ("name", "code", "department__name",)


@admin.register(EmploymentType)
class EmploymentTypeAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ("name", "code", "active",)
    search_fields = ("name", "code",)


@admin.register(ManagementLevel)
class ManagementLevelAdmin(ActiveAdminMixin, admin.ModelAdmin):
    list_display = ("order", "name", "code", "can_manage_people", "active")
    list_editable = ("name", "can_manage_people", "active")
    search_fields = ("name", "code")
    ordering = ("order",)


@admin.register(JobTitle)
class JobTitleAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ("name", "code", "active",)
    search_fields = ("name", "code",)


@admin.register(JobRole)
class JobRoleAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ("name", "code", "active",)
    list_filter = ("active",)
    search_fields = ("name", "code",)


@admin.register(CareerLevel)
class CareerLevelAdmin(ActiveAdminMixin, admin.ModelAdmin,):
    list_display = ( "order", "name", "code", "active",)
    list_editable = ("name", "active",)
    ordering = ("order",)
    search_fields = ("name", "code",)
