from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee
from apps.organization.models import (Department, EmploymentType, JobTitle)


class EvaluationPeriod(TimeStampedModel):
    """
    Performans Dönemi
    """
    name = models.CharField(max_length=100)

    start_date = models.DateField()
    end_date = models.DateField()

    evaluation_start_date = models.DateField(null=True, blank=True)
    evaluation_end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError(
                "Dönem bitiş tarihi başlangıç tarihinden sonra olmalıdır."
            )

        if (
            self.evaluation_start_date
            and self.evaluation_end_date
            and self.evaluation_end_date < self.evaluation_start_date
        ):
            raise ValidationError(
                "Değerlendirme bitiş tarihi başlangıç tarihinden önce olamaz."
            )

    def __str__(self):
        return self.name


class PerformanceCriterion(TimeStampedModel):
    """
    Performans Kriterleri
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=60, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PerformanceTemplate(TimeStampedModel):
    """
    Performans Şablonu
    """
    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def max_score(self):
        return (
                self.criteria.aggregate(
                    total=Sum("max_score")
                )["total"]
                or Decimal("0")
        )

    def validate_total_score(self):
        if self.max_score != Decimal("100"):
            raise ValidationError(
                f"Performans şablonunun toplam puanı "
                f"100 olmalıdır. Mevcut toplam: {self.max_score}"
            )


class PerformanceTemplateCriterion(TimeStampedModel):
    """
    Şablon kriterleri
    """
    template = models.ForeignKey(PerformanceTemplate, on_delete=models.CASCADE, related_name="criteria")
    criterion = models.ForeignKey(PerformanceCriterion, on_delete=models.PROTECT)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "criterion"],
                name="unique_template_criterion",
            ),
        ]

    def clean(self):
        if self.max_score <= 0:
            raise ValidationError(
                "Maksimum kriter puanı sıfırdan büyük olmalıdır."
            )


class ReviewerRole(TimeStampedModel):
    """
    Değerlendirici Rolleri
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=60, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ReviewerScheme(TimeStampedModel):
    """
    Değerlendirme Şeması
    """
    name = models.CharField(max_length=150)
    performance_template = models.ForeignKey(PerformanceTemplate, on_delete=models.PROTECT, related_name="reviewer_schemes")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ReviewerSchemeItem(TimeStampedModel):
    """
    Değerlendirme Şema Elemanları
    """
    scheme = models.ForeignKey(ReviewerScheme, on_delete=models.CASCADE, related_name="items")
    reviewer_role = models.ForeignKey(ReviewerRole, on_delete=models.PROTECT)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "reviewer_role"],
                name="unique_scheme_reviewer_role",
            ),
        ]

    def clean(self):
        if self.weight <= 0:
            raise ValidationError(
                "Değerlendirici ağırlığı sıfırdan büyük olmalıdır."
            )

        if self.weight > 100:
            raise ValidationError(
                "Değerlendirici ağırlığı 100'den büyük olamaz."
            )


class EvaluationProfile(TimeStampedModel):
    """
    Değerlendirmenin hangi şemaya ait olduğunu tutar.
    """
    name = models.CharField(max_length=150)
    reviewer_scheme = models.ForeignKey(ReviewerScheme, on_delete=models.PROTECT, related_name="profiles")
    job_title = models.ForeignKey(JobTitle, null=True, blank=True, on_delete=models.PROTECT)
    employment_type = models.ForeignKey(EmploymentType, null=True, blank=True, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    priority = models.PositiveIntegerField(default=100)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "name"]


class EvaluationStatus(TimeStampedModel):
    """
    Dönem Değerlendirmesi Durumları
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=60, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PerformanceEvaluation(TimeStampedModel):
    """
    Dönem Değerlendirmesi
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="performance_evaluations")
    period = models.ForeignKey(EvaluationPeriod, on_delete=models.PROTECT, related_name="evaluations")
    template = models.ForeignKey(PerformanceTemplate, on_delete=models.PROTECT)
    reviewer_scheme = models.ForeignKey(ReviewerScheme, on_delete=models.PROTECT)
    status = models.ForeignKey(EvaluationStatus, on_delete=models.PROTECT)
    final_performance_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period"],
                name="unique_employee_evaluation_period",
            ),
        ]


class PerformanceEvaluationReviewer(TimeStampedModel):
    """
    Şemadaki ağırlığı snapshot olarak buraya yazılıyor.
    """
    evaluation = models.ForeignKey(
        PerformanceEvaluation,
        on_delete=models.CASCADE,
        related_name="reviewers",
    )

    reviewer_employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="performance_reviews_given",
    )

    reviewer_role = models.ForeignKey(
        ReviewerRole,
        on_delete=models.PROTECT,
    )

    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    raw_score = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    weighted_score = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "evaluation",
                    "reviewer_employee",
                    "reviewer_role",
                ],
                name="unique_evaluation_reviewer",
            ),
        ]


class PerformanceCriterionScore(TimeStampedModel):
    """
    Kriter Puanları
    """
    reviewer = models.ForeignKey(PerformanceEvaluationReviewer, on_delete=models.CASCADE, related_name="criterion_scores")
    criterion = models.ForeignKey(PerformanceCriterion, on_delete=models.PROTECT)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reviewer", "criterion"],
                name="unique_reviewer_criterion_score",
            ),
        ]

    def clean(self):
        if self.score < 0:
            raise ValidationError(
                "Puan sıfırdan küçük olamaz."
            )

        if self.score > self.max_score:
            raise ValidationError(
                "Verilen puan maksimum kriter puanını aşamaz."
            )