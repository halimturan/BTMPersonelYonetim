from django.contrib import admin
from apps.employees.models import (EducationLevel, Employee, EmployeeAssignmentHistory, EmployeeDepartmentHistory,
    EmployeeEducation, EmployeeLevelHistory, EmployeeTitleHistory, EmployeeUpgrade, EmployeeExperience,
    EmployeeManagementLevelHistory
)
from apps.employees.services.upgrade import EmployeeUpgradeService
from django.db import transaction
from apps.employees.forms import EmployeeUpgradeAdminForm


class EmployeeEducationInline(admin.TabularInline):
    verbose_name = "Eğitimler"
    verbose_name_plural = "Eğitimler"
    model = EmployeeEducation
    extra = 0
    fields = ("education_level", "school_name", "department_name", "graduation_date", "is_primary_for_scoring")


class EmployeeManagementLevelHistoryInline(admin.TabularInline):
    model = EmployeeManagementLevelHistory
    extra = 0
    fields = ("management_level", "start_date", "end_date")
    ordering = ("-start_date",)

class EmployeeAssignmentHistoryInline(admin.TabularInline):
    verbose_name = "İş Kolu Geçmişi"
    verbose_name_plural = "İş Kolu Geçmişi"
    model = EmployeeAssignmentHistory
    extra = 0
    fields = ("job_role", "start_date", "end_date", "description")


class EmployeeTitleHistoryInline(admin.TabularInline):
    verbose_name = "Ünvan Geçmişi"
    verbose_name_plural = "Ünvan Geçmişi"
    model = EmployeeTitleHistory
    extra = 0
    fields = ("job_title", "start_date", "end_date")


class EmployeeDepartmentHistoryInline(admin.TabularInline):
    verbose_name = "Şeflik Geçmişi"
    verbose_name_plural = "Şeflik Geçmişi"
    model = EmployeeDepartmentHistory
    extra = 0
    fields = ("department", "unit", "start_date", "end_date")


class EmployeeLevelHistoryInline(admin.TabularInline):
    verbose_name = "Seviye Geçmişi"
    verbose_name_plural = "Seviye Geçmişi"
    model = EmployeeLevelHistory
    extra = 0
    fields = ("job_role", "level", "start_date", "end_date", "reason")


class EmployeeExperienceInline(admin.TabularInline):
    model = EmployeeExperience
    extra = 0
    fields = ("source", "start_date", "end_date", "description")
    ordering = ("-start_date",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "personnel_no",
        "first_name",
        "last_name",
        "gender",
        "phone",
        "employment_type",
        "current_management_level",
        "is_active"
    )
    list_filter = ("is_active", "employment_type", "current_management_level",)
    search_fields = ("personnel_no", "first_name", "last_name")
    list_select_related = ("employment_type",)
    ordering = ("first_name", "last_name",)
    list_per_page = 10

    inlines = (
        EmployeeEducationInline, EmployeeAssignmentHistoryInline, EmployeeTitleHistoryInline,
        EmployeeDepartmentHistoryInline, EmployeeLevelHistoryInline, EmployeeExperienceInline,
        EmployeeManagementLevelHistoryInline
    )

    fieldsets = (
        (
            "Personel Bilgileri",
            {
                "fields": (
                    "personnel_no",
                    "domain_name",
                    "first_name",
                    "last_name",
                    "gender",
                    "phone",
                    "employment_type",
                    "current_management_level",
                    "is_active",
                )
            },
        ),
    )

    @admin.display(
        description="Birim"
    )
    def get_current_unit(self, obj):
        return obj.current_unit or "-"

    @admin.display(
        description="Unvan"
    )
    def get_current_title(self, obj):
        return obj.current_title or "-"

    @admin.display(description="Yönetim Seviyesi")
    def get_management_level(self, obj):
        return obj.current_management_level or "-"

    @admin.display(
        description="İş Kolu"
    )
    def get_current_job_role(self, obj):
        return obj.current_job_role or "-"


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "code", "active",)
    list_editable = ("name", "active",)
    search_fields = ("name", "code",)
    list_filter = ("active",)
    ordering = ("order",)


@admin.register(EmployeeUpgrade)
class EmployeeUpgradeAdmin(admin.ModelAdmin):

    form = EmployeeUpgradeAdminForm

    list_display = (
        "employee",
        "from_job_role",
        "from_level",
        "to_job_role",
        "to_level",
        "effective_date",
    )

    list_filter = (
        "from_job_role",
        "to_job_role",
        "from_level",
        "to_level",
        "effective_date",
    )

    search_fields = (
        "employee__personnel_no",
        "employee__first_name",
        "employee__last_name",
    )

    ordering = (
        "-effective_date",
        "-pk",
    )

    # ==========================================
    # ADD / CHANGE EKRANLARI
    # ==========================================

    def get_fields(
        self,
        request,
        obj=None,
    ):

        # Mevcut upgrade görüntülenirken
        if obj:
            return (
                "employee",
                "from_job_role",
                "from_level",
                "to_job_role",
                "to_level",
                "effective_date",
                "reason",
                "period_score",
            )

        # Yeni upgrade oluşturulurken
        return (
            "employee",
            "to_job_role",
            "to_level",
            "effective_date",
            "reason",
            "period_score",
        )

    # ==========================================
    # UYGULANMIŞ UPGRADE DEĞİŞTİRİLMESİN
    # ==========================================

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):

        if obj:
            return (
                "employee",
                "from_job_role",
                "from_level",
                "to_job_role",
                "to_level",
                "effective_date",
                "period_score",
            )

        return ()

    # ==========================================
    # KAYDET
    # ==========================================

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):

        # Mevcut upgrade'da sadece
        # reason gibi izin verilen alanlar
        # değişebilir.
        if change:
            super().save_model(
                request,
                obj,
                form,
                change,
            )
            return

        # Form.clean() burada:
        #
        # from_job_role
        # from_level
        #
        # değerlerini obj üzerine zaten koydu.

        super().save_model(
            request,
            obj,
            form,
            change,
        )

        EmployeeUpgradeService(
            obj
        ).apply()