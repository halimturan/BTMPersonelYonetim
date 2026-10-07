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
    education_level = models.ForeignKey(EducationLevel, null=True, blank=True, on_delete=models.PROTECT, verbose_name="Mezuniyet")
    score = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Puan")

    class Meta:
        verbose_name_plural = "Mezuniyet Puanları"

    def clean(self):
        if not 0 <= self.score <= 100:
            raise ValidationError(
                "Mezuniyet puanı 0-100 arasında olmalıdır."
            )


class JobRoleScoreRule(EffectiveDatedModel, TimeStampedModel):
    """
    İş kolu puanı
    """
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name="score_rules", verbose_name="İş Kolu")
    score = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Puan")

    class Meta:
        verbose_name_plural = "İş Kolu Puanları"

    def clean(self):
        if not 0 <= self.score <= 100:
            raise ValidationError(
                "İş kolu puanı 0-100 arasında olmalıdır."
            )


class ExperienceSource(TimeStampedModel):
    """
    Tecrübe kaynağı
    """
    name = models.CharField(max_length=150, verbose_name="İsim")
    code = models.CharField(max_length=60, unique=True, verbose_name="Kod")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Deneyim Kaynakları"


class ExperienceScoreRule(EffectiveDatedModel, TimeStampedModel):
    name = models.CharField(max_length=150, verbose_name="İsim")
    experience_source = models.ForeignKey(ExperienceSource, on_delete=models.PROTECT, verbose_name="Deneyim Kaynağı",
                                          help_text="Hangi alan baz alınacak? Örn: IT Tecrübesi")
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100, verbose_name="Maximum Skor")
    decay_factor = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Yıpranma Faktörü",
                                       help_text="Tecrübe formülündeki blüöü ifade eder. 100 × (1 - e^(-Yıl / yıpranma faktörü))")

    class Meta:
        verbose_name_plural = "Deneyim Puan Hesabı"

    def clean(self):
        if self.max_score <= 0:
            raise ValidationError(
                "Maksimum skor sıfırdan büyük olmalıdır."
            )

        if self.decay_factor <= 0:
            raise ValidationError(
                "Decay factor sıfırdan büyük olmalıdır."
            )


class RateRevision(TimeStampedModel):
    """
    İş kolu ücret tarifelerine uygulanan
    toplu ücret revizyonu.

    Örnek:
        2027 / 1. Dönem Genel Zam
        01.01.2027
        %15
    """
    name = models.CharField(max_length=150, verbose_name="Revizyon Adı")
    effective_date = models.DateField(verbose_name="Geçerlilik Tarihi")
    percentage = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="Zam Oranı (%)")
    applied_at = models.DateTimeField(null=True, blank=True, verbose_name="Uygulanma Tarihi")

    class Meta:
        verbose_name = "Ücret Revizyonu"
        verbose_name_plural = "Ücret Revizyonları"
        ordering = ["-effective_date", "-pk"]

    def clean(self):
        super().clean()

        if self.percentage <= 0:
            raise ValidationError({"percentage": "Zam oranı sıfırdan büyük olmalıdır."})

    def __str__(self):
        return f"{self.name} - %{self.percentage}"


class JobLevelRate(EffectiveDatedModel, TimeStampedModel):
    """
    İş Kolu - Seviye ücretleri
    """
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name="level_rates", verbose_name="İş Kolu")
    level = models.ForeignKey(CareerLevel, on_delete=models.PROTECT, verbose_name="Seviye")
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Tutar")
    revision = models.ForeignKey(RateRevision, null=True, blank=True, on_delete=models.PROTECT,
        related_name="rates", verbose_name="Ücret Revizyonu",
    )

    def __str__(self):
        return f"{self.job_role} - {self.level} - {self.amount}₺"

    class Meta:
        verbose_name_plural = "İş Kolu Ücretleri"
        constraints = [
            models.UniqueConstraint(
                fields=["job_role", "level", "valid_from",],
                name="unique_job_level_rate_date",
            ),
        ]


class ScoreComponent(TimeStampedModel):
    """
    Nihai skor bileşenleri. (İş Kolu,Mezuniyet,Tecrübe,Performans)
    """
    name = models.CharField(max_length=150, verbose_name="İsim")
    code = models.CharField(max_length=60, unique=True, verbose_name="Kod")
    active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Puanlama Bileşenleri"


class ScoreFormula(EffectiveDatedModel, TimeStampedModel):
    """
    Skor formülü
    """
    name = models.CharField(max_length=150, verbose_name="İsim")
    description = models.TextField(blank=True, verbose_name="Açıklama")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Puan Formülü"


class ScoreFormulaComponent(TimeStampedModel):
    """
    Formül bileşenleri
    İş Kolu        20
    Mezuniyet      20
    Tecrübe        15
    Performans     45
    """
    formula = models.ForeignKey(ScoreFormula, on_delete=models.CASCADE, related_name="components", verbose_name="Formül")
    component = models.ForeignKey(ScoreComponent, on_delete=models.PROTECT, verbose_name="Bileşenler")
    weight = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Ağırlık")
    order = models.PositiveIntegerField(default=0, verbose_name="Sıra")

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Puan Formül Bileşenleri"
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

    def __str__(self):
        return f"{self.employee} - {self.final_score}"

    class Meta:
        verbose_name_plural = "Personel Dönem Skorları"
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


class UpgradeRecommendationRule(TimeStampedModel):
    """
    Upgrade öneri motorunda kullanılacak kurallar.

    İlk sürümde tek aktif kural seti kullanılabilir.
    Daha sonra dönem veya tarih bazlı kural setlerine
    geçebilmek için ayrı model olarak tutuluyor.
    """

    name = models.CharField(max_length=150, verbose_name="Kural Seti")
    min_period_count = models.PositiveSmallIntegerField(default=3, verbose_name="Minimum Dönem Sayısı")
    min_average_score = models.DecimalField(max_digits=6, decimal_places=2, default=85,
        verbose_name="Minimum Ortalama Nihai Skor",
    )
    min_period_score = models.DecimalField(max_digits=6, decimal_places=2, default=75,
        verbose_name="Minimum Tek Dönem Skoru",
    )
    experience_tolerance_years = models.DecimalField(max_digits=4, decimal_places=1, default=2,
        verbose_name="Tecrübe Karşılaştırma Toleransı",
        help_text="Benzer personel belirlenirken kullanılacak ± yıl toleransı.",
    )
    min_peer_count = models.PositiveSmallIntegerField(default=3, verbose_name="Minimum Benzer Personel Sayısı")
    candidate_peer_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=60,
        verbose_name="Adaylık İçin Üst Seviye Oranı (%)",
    )
    strong_peer_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=75,
        verbose_name="Güçlü Adaylık İçin Üst Seviye Oranı (%)",
    )
    active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Upgrade Öneri Kuralı"
        verbose_name_plural = "Upgrade Öneri Kuralları"

    def __str__(self):
        return self.name


class EmployeeUpgradeRecommendation(TimeStampedModel):

    class Status(models.TextChoices):
        INSUFFICIENT_DATA = "INSUFFICIENT_DATA", "Yetersiz Veri"
        WATCH = "WATCH", "İzlenmeli"
        CANDIDATE = "CANDIDATE", "Upgrade Adayı"
        STRONG = "STRONG", "Güçlü Upgrade Adayı"
        APPROVED = "APPROVED", "Onaylandı"
        REJECTED = "REJECTED", "Uygun Görülmedi"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE,
        related_name="upgrade_recommendations", verbose_name="Personel"
    )
    period = models.ForeignKey("performance.EvaluationPeriod",on_delete=models.PROTECT,
        related_name="upgrade_recommendations", verbose_name="Dönem",
    )
    rule = models.ForeignKey(UpgradeRecommendationRule, on_delete=models.PROTECT, related_name="recommendations",
        verbose_name="Kural Seti",
    )
    job_role = models.ForeignKey("organization.JobRole", on_delete=models.PROTECT, verbose_name="İş Kolu",
        related_name="upgrade_recommendations",
    )
    current_level = models.ForeignKey("organization.CareerLevel", on_delete=models.PROTECT, related_name="+",
        verbose_name="Mevcut Seviye",
    )
    recommended_level = models.ForeignKey("organization.CareerLevel", on_delete=models.PROTECT,
        related_name="+", verbose_name="Önerilen Seviye",
    )
    recommendation_score = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Öneri Puanı")
    status = models.CharField(max_length=20, choices=Status.choices, verbose_name="Durum")
    explanation = models.JSONField(default=dict, blank=True, verbose_name="Öneri Açıklaması")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="İncelenme Tarihi")
    review_note = models.TextField(blank=True, verbose_name="Yönetici Notu")

    class Meta:
        verbose_name = "Upgrade Önerisi"
        verbose_name_plural = "Upgrade Önerileri"

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period", "rule"],
                name=(
                    "unique_employee_upgrade_"
                    "recommendation"
                ),
            ),
        ]

    def __str__(self):
        return f"{self.employee} - {self.current_level} → {self.recommended_level}"
