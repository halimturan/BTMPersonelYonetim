from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import (EffectiveDatedModel, TimeStampedModel)
from apps.employees.models import EducationLevel, Employee
from apps.organization.models import CareerLevel, JobRole
from apps.performance.models import EvaluationPeriod


class EducationScoreRule(EffectiveDatedModel, TimeStampedModel):
    """
    Mezuniyet Puanı
    """
    name = models.CharField(max_length=200, verbose_name="İsim")
    education_level = models.ForeignKey(EducationLevel, null=True, blank=True, on_delete=models.PROTECT, verbose_name="Mezuniyet")
    is_it_related = models.BooleanField(null=True, blank=True)
    is_engineering = models.BooleanField(null=True, blank=True, )
    is_open_education = models.BooleanField(null=True, blank=True, verbose_name="Açık Öğretim mi?")
    score = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Puan")
    priority = models.PositiveIntegerField(default=100)

    class Meta:
        verbose_name_plural = "Mezuniyet Puanları"
        ordering = ["priority"]

    def clean(self):
        if not 0 <= self.score <= 100:
            raise ValidationError(
                "Mezuniyet puanı 0-100 arasında olmalıdır."
            )


class JobRoleScoreRule(EffectiveDatedModel, TimeStampedModel):
    """
    İş kolu puanı
    """
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name="score_rules")
    score = models.DecimalField(max_digits=6, decimal_places=2)

    def clean(self):
        if not 0 <= self.score <= 100:
            raise ValidationError(
                "İş kolu puanı 0-100 arasında olmalıdır."
            )


class ExperienceSource(TimeStampedModel):
    """
    Tecrübe kaynağı
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=60, unique=True)

    field_name = models.CharField(
        max_length=100,
        help_text=(
            "Employee modelinde kullanılacak tarih alanı. "
            "Örn: it_start_date"
        ),
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ExperienceScoreRule(EffectiveDatedModel, TimeStampedModel):
    name = models.CharField(max_length=150)
    experience_source = models.ForeignKey(ExperienceSource, on_delete=models.PROTECT)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    decay_factor = models.DecimalField(max_digits=10, decimal_places=4)

    def clean(self):
        if self.max_score <= 0:
            raise ValidationError(
                "Maksimum skor sıfırdan büyük olmalıdır."
            )

        if self.decay_factor <= 0:
            raise ValidationError(
                "Decay factor sıfırdan büyük olmalıdır."
            )


class JobLevelRate(EffectiveDatedModel, TimeStampedModel):
    """
    Seviye tutarları
    """
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name="level_rates")
    level = models.ForeignKey(CareerLevel, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name_plural = "İş Kolu Ücretleri"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "job_role",
                    "level",
                    "valid_from",
                ],
                name="unique_job_level_rate_date",
            ),
        ]


class ScoreComponent(TimeStampedModel):
    """
    Nihai skor bileşenleri. (İş Kolu,Mezuniyet,Tecrübe,Performans)
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=60, unique=True)

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ScoreFormula(EffectiveDatedModel, TimeStampedModel):
    """
    Skor formülü
    """
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ScoreFormulaComponent(TimeStampedModel):
    """
    Formül bileşenleri
    İş Kolu        20
    Mezuniyet      20
    Tecrübe        15
    Performans     45
    """
    formula = models.ForeignKey(ScoreFormula, on_delete=models.CASCADE, related_name="components")
    component = models.ForeignKey(ScoreComponent, on_delete=models.PROTECT)
    weight = models.DecimalField(max_digits=6, decimal_places=2)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["formula", "component"],
                name="unique_formula_component",
            ),
        ]

    def clean(self):
        if self.weight <= 0:
            raise ValidationError(
                "Ağırlık sıfırdan büyük olmalıdır."
            )

        if self.weight > 100:
            raise ValidationError(
                "Ağırlık 100'den büyük olamaz."
            )


class EmployeePeriodScore(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="period_scores")
    period = models.ForeignKey(EvaluationPeriod, on_delete=models.PROTECT, related_name="employee_scores")
    formula = models.ForeignKey(ScoreFormula, on_delete=models.PROTECT)
    final_score = models.DecimalField(max_digits=8, decimal_places=4)
    locked = models.BooleanField(default=False)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period"],
                name="unique_employee_period_score",
            ),
        ]


class EmployeePeriodScoreComponent(TimeStampedModel):
    period_score = models.ForeignKey(EmployeePeriodScore, on_delete=models.CASCADE, related_name="components")
    component = models.ForeignKey(ScoreComponent, on_delete=models.PROTECT)
    raw_score = models.DecimalField(max_digits=8, decimal_places=4)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    weighted_score = models.DecimalField(max_digits=8, decimal_places=4)
    source_data = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["period_score", "component"],
                name="unique_period_score_component",
            ),
        ]
