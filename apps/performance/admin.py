from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from apps.performance.models import (EvaluationPeriod, EvaluationProfile, EvaluationStatus, PerformanceCriterion,
    PerformanceCriterionScore, PerformanceEvaluation, PerformanceEvaluationReviewer, PerformanceTemplate,
    PerformanceTemplateCriterion, ReviewerRole, ReviewerScheme, ReviewerSchemeItem,
)


class PerformanceTemplateCriterionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        total = Decimal("0")

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            max_score = (
                form.cleaned_data.get("max_score")
            )

            if max_score is not None:
                total += max_score

        if total != Decimal("100"):
            raise ValidationError(
                f"Performans kriterlerinin toplam puanı "
                f"100 olmalıdır. Mevcut toplam: {total}"
            )


class PerformanceTemplateCriterionInline(admin.TabularInline):
    model = PerformanceTemplateCriterion
    formset = PerformanceTemplateCriterionInlineFormSet
    extra = 0
    fields = ("order", "criterion", "max_score", "required")


@admin.register(PerformanceTemplate)
class PerformanceTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "valid_from", "valid_to", "active")
    list_filter = ("active",)
    search_fields = ("name",)
    inlines = (PerformanceTemplateCriterionInline,)


@admin.register(PerformanceCriterion)
class PerformanceCriterionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active",)
    list_filter = ("active",)
    search_fields = ("name", "code", "description")


class ReviewerSchemeItemInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        total = Decimal("0")

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            weight = form.cleaned_data.get("weight")

            if weight is not None:
                total += weight

        if total != Decimal("100"):
            raise ValidationError(
                f"Değerlendirici ağırlıkları toplamı "
                f"100 olmalıdır. Mevcut toplam: {total}"
            )


class ReviewerSchemeItemInline(admin.TabularInline):
    model = ReviewerSchemeItem
    formset = ReviewerSchemeItemInlineFormSet
    extra = 0
    fields = ("order", "reviewer_role", "management_level", "weight",)


@admin.register(ReviewerScheme)
class ReviewerSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "performance_template", "valid_from", "valid_to", "active")
    list_filter = ("active",)
    search_fields = ("name",)
    inlines = (ReviewerSchemeItemInline,)


@admin.register(ReviewerRole)
class ReviewerRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active")
    list_filter = ("active",)
    search_fields = ("name", "code",)


@admin.register(EvaluationProfile)
class EvaluationProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "management_level", "job_title", "employment_type", "department", "reviewer_scheme",
                    "priority", "active")
    list_filter = ("active", "management_level", "employment_type", "department",)
    search_fields = ("name", "job_title__name", "management_level__name",)


@admin.register(EvaluationPeriod)
class EvaluationPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "evaluation_start_date", "evaluation_end_date", "is_active",
                    "is_locked")
    list_filter = ("is_active", "is_locked",)
    search_fields = ("name",)


@admin.register(EvaluationStatus)
class EvaluationStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active",)
    list_filter = ("active",)
    search_fields = ("name", "code",)


class PerformanceEvaluationReviewerInline(admin.TabularInline):
    model = PerformanceEvaluationReviewer
    extra = 0
    readonly_fields = ("raw_score", "weighted_score", "submitted_at")
    fields = ("reviewer_employee", "reviewer_role", "weight", "raw_score", "weighted_score", "submitted_at")


@admin.register(PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "period", "template", "reviewer_scheme", "status", "final_performance_score", "completed_at",
    )
    list_filter = ("period", "status", "template",)
    search_fields = ("employee__personnel_no", "employee__first_name", "employee__last_name",)
    readonly_fields = ("final_performance_score", "completed_at", "created_at", "updated_at")

    inlines = (PerformanceEvaluationReviewerInline,)


class PerformanceCriterionScoreInline(admin.TabularInline):
    model = PerformanceCriterionScore
    extra = 0
    fields = ("criterion", "score", "max_score", "comment")


@admin.register(PerformanceEvaluationReviewer)
class PerformanceEvaluationReviewerAdmin(admin.ModelAdmin):
    list_display = (
        "evaluation", "reviewer_employee", "reviewer_role", "weight", "raw_score", "weighted_score", "submitted_at",
    )
    list_filter = ("reviewer_role", "submitted_at")
    search_fields = (
        "evaluation__employee__first_name",
        "evaluation__employee__last_name",
        "reviewer_employee__first_name",
        "reviewer_employee__last_name",
    )
    readonly_fields = ("raw_score", "weighted_score", "submitted_at", "created_at", "updated_at")
    inlines = (PerformanceCriterionScoreInline,)
