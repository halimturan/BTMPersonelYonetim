from decimal import Decimal
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from apps.scoring.models import (EducationScoreRule, EmployeePeriodScore, EmployeePeriodScoreComponent,
                                 ExperienceScoreRule, ExperienceSource, JobLevelRate, JobRoleScoreRule, ScoreComponent,
                                 ScoreFormula, ScoreFormulaComponent,)


@admin.register(ScoreComponent)
class ScoreComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active")
    list_filter = ("active",)
    search_fields = ("name", "code",)

class ScoreFormulaComponentInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        total = Decimal("0")

        for form in self.forms:

            if not hasattr(form, "cleaned_data",):
                continue

            if form.cleaned_data.get("DELETE", False,):
                continue

            weight = form.cleaned_data.get("weight")

            if weight is not None:
                total += weight

        if total != Decimal("100"):
            raise ValidationError(
                f"Skor bileşeni ağırlıkları toplamı "
                f"%100 olmalıdır. "
                f"Mevcut toplam: %{total}"
            )


class ScoreFormulaComponentInline(admin.TabularInline):
    model = ScoreFormulaComponent
    formset = ScoreFormulaComponentInlineFormSet
    extra = 0
    autocomplete_fields = ("component",)
    fields = ("order", "component", "weight",)


@admin.register(ScoreFormula)
class ScoreFormulaAdmin(admin.ModelAdmin):
    list_display = ("name", "valid_from", "valid_to", "active",)
    list_filter = ("active", "valid_from", "valid_to",)
    search_fields = ("name", "description",)
    inlines = (ScoreFormulaComponentInline,)
    attrs = {"class": "noSelect2DAL"}


@admin.register(EducationScoreRule)
class EducationScoreRuleAdmin(admin.ModelAdmin):
    list_display = ("education_level", "score", "valid_from", "valid_to", "active")
    list_filter = ("active", "education_level")
    search_fields = ("education_level__name",)
    autocomplete_fields = ("education_level",)


@admin.register(JobRoleScoreRule)
class JobRoleScoreRuleAdmin(admin.ModelAdmin):
    list_display = ("job_role", "score", "valid_from", "valid_to", "active",)
    list_filter = ("active", "job_role",)
    search_fields = ("job_role__name",)
    autocomplete_fields = ("job_role",)
    list_editable = ("score", "active",)


@admin.register(ExperienceSource)
class ExperienceSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active",)
    list_filter = ("active",)
    search_fields = ("name", "code")


@admin.register(ExperienceScoreRule)
class ExperienceScoreRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "experience_source", "max_score", "decay_factor", "valid_from", "valid_to", "active",)
    list_filter = ("active", "experience_source")
    search_fields = ("name",)
    autocomplete_fields = ("experience_source",)


@admin.register(JobLevelRate)
class JobLevelRateAdmin(admin.ModelAdmin):
    list_display = ("job_role", "level", "amount", "valid_from", "valid_to", "active",)
    list_filter = ("active", "job_role", "level",)
    search_fields = ("job_role__name", "level__name",)
    autocomplete_fields = ("job_role", "level",)
    list_editable = ("amount",)
    list_per_page = 10


class EmployeePeriodScoreComponentInline(admin.TabularInline):
    model = EmployeePeriodScoreComponent
    extra = 0
    autocomplete_fields = ("component",)
    readonly_fields = ("component", "raw_score", "weight", "weighted_score", "source_data")
    can_delete = False

    def has_add_permission(self, request, obj=None,):
        return False


@admin.register(EmployeePeriodScore)
class EmployeePeriodScoreAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "formula", "final_score", "locked", "calculated_at")
    list_filter = ("period", "formula", "locked")
    search_fields = ("employee__personnel_no", "employee__first_name", "employee__last_name",)
    autocomplete_fields = ("employee", "period", "formula")
    readonly_fields = ("final_score", "calculated_at", "created_at", "updated_at")
    inlines = (EmployeePeriodScoreComponentInline,)
