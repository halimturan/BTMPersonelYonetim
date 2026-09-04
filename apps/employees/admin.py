from django.contrib import admin

from apps.employees.models import (EducationLevel, Employee, EmployeeAssignmentHistory, EmployeeDepartmentHistory,
    EmployeeEducation, EmployeeLevelHistory, EmployeeReportingLine, EmployeeTitleHistory, EmployeeUpgrade,
    ReportingRelationType,
)


class EmployeeEducationInline(admin.TabularInline):
    model = EmployeeEducation
    extra = 0
    autocomplete_fields = ("education_level",)
    fields = (
        "education_level", "school_name", "department_name", "graduation_date", "is_it_related", "is_engineering",
        "is_open_education", "is_primary_for_scoring",
    )


class EmployeeAssignmentHistoryInline(admin.TabularInline):
    model = EmployeeAssignmentHistory
    extra = 0

    autocomplete_fields = (
        "job_role",
    )

    fields = (
        "job_role",
        "start_date",
        "end_date",
        "description",
    )


class EmployeeTitleHistoryInline(admin.TabularInline):
    model = EmployeeTitleHistory
    extra = 0

    autocomplete_fields = (
        "job_title",
    )

    fields = (
        "job_title",
        "start_date",
        "end_date",
    )


class EmployeeDepartmentHistoryInline(admin.TabularInline):
    model = EmployeeDepartmentHistory
    extra = 0

    autocomplete_fields = (
        "department",
        "unit",
    )

    fields = (
        "department",
        "unit",
        "start_date",
        "end_date",
    )


class EmployeeLevelHistoryInline(admin.TabularInline):
    model = EmployeeLevelHistory
    extra = 0

    autocomplete_fields = (
        "job_role",
        "level",
    )

    fields = (
        "job_role",
        "level",
        "start_date",
        "end_date",
        "reason",
    )


class EmployeeReportingLineInline(admin.TabularInline):
    model = EmployeeReportingLine

    fk_name = "employee"

    extra = 0

    autocomplete_fields = (
        "manager",
        "relation_type",
    )

    fields = (
        "manager",
        "relation_type",
        "start_date",
        "end_date",
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "personnel_no", "first_name", "last_name", "employment_type", "institution_start_date",
        "it_start_date", "is_active",
    )
    list_filter = ("is_active", "employment_type",)
    search_fields = ("personnel_no", "first_name", "last_name", "ikys_reference",)
    autocomplete_fields = ("employment_type",)
    list_select_related = ("employment_type",)
    ordering = ("first_name", "last_name",)

    inlines = (
        EmployeeEducationInline, EmployeeAssignmentHistoryInline, EmployeeTitleHistoryInline,
        EmployeeDepartmentHistoryInline, EmployeeLevelHistoryInline, EmployeeReportingLineInline,
    )

    fieldsets = (
        (
            "Personel Bilgileri",
            {
                "fields": ("personnel_no", "first_name", "last_name", "employment_type", "is_active",)
            },
        ),
        (
            "Tecrübe Tarihleri",
            {
                "fields": ("institution_start_date", "professional_start_date", "it_start_date",)
            },
        ),
        (
            "Entegrasyon",
            {
                "fields": ("ikys_reference",)
            },
        ),
    )


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "code", "active",)
    list_editable = ("name", "active",)
    search_fields = ("name", "code",)
    list_filter = ("active",)
    ordering = ("order",)


@admin.register(ReportingRelationType)
class ReportingRelationTypeAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "code", "active",)
    list_editable = ("name", "active",)
    search_fields = ("name", "code",)
    list_filter = ("active",)
    ordering = ("order",)


@admin.register(EmployeeReportingLine)
class EmployeeReportingLineAdmin(admin.ModelAdmin):
    list_display = ("employee", "manager", "relation_type", "start_date", "end_date",)
    list_filter = ("relation_type","start_date","end_date",)
    search_fields = ("employee__personnel_no", "employee__first_name", "employee__last_name", "manager__personnel_no",
                     "manager__first_name", "manager__last_name",)
    autocomplete_fields = ("employee", "manager", "relation_type",)
    list_select_related = ("employee", "manager", "relation_type",)


@admin.register(EmployeeUpgrade)
class EmployeeUpgradeAdmin(admin.ModelAdmin):
    list_display = ("employee", "job_role", "from_level", "to_level", "effective_date",)
    list_filter = ("job_role", "from_level", "to_level", "effective_date",)
    search_fields = ("employee__personnel_no", "employee__first_name", "employee__last_name", "reason",)
    autocomplete_fields = ("employee", "job_role", "from_level", "to_level", "period_score",)
    date_hierarchy = "effective_date"
