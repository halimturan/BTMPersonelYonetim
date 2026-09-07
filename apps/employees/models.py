from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.organization.models import (CareerLevel, Department, EmploymentType, JobRole, JobTitle, Unit,
                                      OrganizationPosition)


class Employee(TimeStampedModel):
    personnel_no = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Sicil No")
    first_name = models.CharField(max_length=100, verbose_name="Ad")
    last_name = models.CharField(max_length=100, verbose_name="Soyad")
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, related_name="employees", verbose_name="Personel Tipi")

    institution_start_date = models.DateField(null=True, blank=True, verbose_name="Kuruma Başlangıç Tarihi")
    professional_start_date = models.DateField(null=True, blank=True, verbose_name="Profesyonel Çalışma Tarihi")
    it_start_date = models.DateField(null=True, blank=True, verbose_name="IT Sektörüne Başlangıç Tarihi")

    ikys_reference = models.CharField(max_length=150, null=True, blank=True, unique=True, verbose_name="IKYS Referans Kodu")

    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    class Meta:
        verbose_name_plural = "Personeller"
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["personnel_no"]),
            models.Index(fields=["is_active"]),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_assignment(self):
        today = timezone.localdate()

        return (
            self.assignments
            .filter(
                start_date__lte=today,
                end_date__isnull=True,
            )
            .select_related("job_role")
            .first()
        )

    @property
    def current_job_role(self):
        assignment = self.current_assignment

        return (
            assignment.job_role
            if assignment
            else None
        )

    @property
    def current_title_record(self):
        today = timezone.localdate()

        return (
            self.title_history
            .filter(
                start_date__lte=today,
                end_date__isnull=True,
            )
            .select_related("job_title")
            .first()
        )

    @property
    def current_title(self):
        record = self.current_title_record

        return (
            record.job_title
            if record
            else None
        )

    @property
    def current_department_record(self):
        today = timezone.localdate()

        return (
            self.department_history
            .filter(
                start_date__lte=today,
                end_date__isnull=True,
            )
            .select_related(
                "department",
                "unit",
            )
            .first()
        )

    @property
    def current_level_record(self):
        today = timezone.localdate()

        return (
            self.level_history
            .filter(
                start_date__lte=today,
                end_date__isnull=True,
            )
            .select_related(
                "level",
                "job_role",
            )
            .first()
        )

    def __str__(self):
        return f"{self.personnel_no} - {self.full_name}"


class EducationLevel(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Mezuniyetler"
        ordering = ["order"]

    def __str__(self):
        return self.name


class EmployeeEducation(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="educations")
    education_level = models.ForeignKey(EducationLevel, on_delete=models.PROTECT)
    school_name = models.CharField(max_length=250, blank=True)
    department_name = models.CharField(max_length=250, blank=True)
    graduation_date = models.DateField(null=True, blank=True)
    is_it_related = models.BooleanField(default=False)
    is_engineering = models.BooleanField(default=False)
    is_open_education = models.BooleanField(default=False)

    is_primary_for_scoring = models.BooleanField(default=False)

    class Meta:
        ordering = [
            "employee",
            "-is_primary_for_scoring",
            "-graduation_date",
        ]

    def clean(self):
        if not self.is_primary_for_scoring:
            return

        exists = (
            EmployeeEducation.objects
            .filter(
                employee=self.employee,
                is_primary_for_scoring=True,
            )
            .exclude(pk=self.pk)
            .exists()
        )

        if exists:
            raise ValidationError(
                "Bir personelin puanlamada kullanılan "
                "yalnızca bir aktif mezuniyeti olabilir."
            )


def validate_history_overlap(
    model,
    employee,
    start_date,
    end_date,
    instance_pk=None,
):
    qs = model.objects.filter(employee=employee)

    if instance_pk:
        qs = qs.exclude(pk=instance_pk)

    if end_date:
        qs = qs.filter(
            start_date__lte=end_date
        )

    qs = qs.filter(
        models.Q(end_date__isnull=True)
        | models.Q(end_date__gte=start_date)
    )

    if qs.exists():
        raise ValidationError(
            "Bu personel için tarih aralığı mevcut "
            "bir kayıtla çakışıyor."
        )


class EmployeeAssignmentHistory(TimeStampedModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.PROTECT,
    )

    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True,
    )

    description = models.TextField(blank=True)

    class Meta:
        ordering = ["employee", "-start_date"]
        indexes = [
            models.Index(
                fields=["employee", "start_date", "end_date"]
            )
        ]

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        validate_history_overlap(
            EmployeeAssignmentHistory,
            self.employee,
            self.start_date,
            self.end_date,
            self.pk,
        )

    def __str__(self):
        return f"{self.employee} - {self.job_role}"


class EmployeeTitleHistory(TimeStampedModel):
    """
    Ünvan (title) geçmişi
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="title_history", verbose_name="Personel")
    job_title = models.ForeignKey(JobTitle, on_delete=models.PROTECT, verbose_name="Resmi Ünvan")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")

    class Meta:
        verbose_name_plural = "Ünvan Geçmişleri"
        ordering = ["employee", "-start_date"]

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        validate_history_overlap(
            EmployeeTitleHistory,
            self.employee,
            self.start_date,
            self.end_date,
            self.pk,
        )

    def __str__(self):
        return f"{self.employee} - {self.job_title}"


class EmployeeDepartmentHistory(TimeStampedModel):
    """
    Departman/Birim Geçmişi
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="department_history",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
    )

    unit = models.ForeignKey(
        Unit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["employee", "-start_date"]

    def clean(self):
        if self.unit and self.unit.department_id != self.department_id:
            raise ValidationError(
                "Birim seçilen departmana bağlı değil."
            )

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        validate_history_overlap(
            EmployeeDepartmentHistory,
            self.employee,
            self.start_date,
            self.end_date,
            self.pk,
        )


class EmployeeLevelHistory(TimeStampedModel):
    """
    Seviye Geçmişi
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="level_history",
    )

    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.PROTECT,
    )

    level = models.ForeignKey(
        CareerLevel,
        on_delete=models.PROTECT,
    )

    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True,
    )

    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["employee", "-start_date"]

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        validate_history_overlap(
            EmployeeLevelHistory,
            self.employee,
            self.start_date,
            self.end_date,
            self.pk,
        )


class EmployeeUpgrade(TimeStampedModel):
    """
    Upgrade işlemleri
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="upgrades")
    job_role = models.ForeignKey(JobRole, on_delete=models.PROTECT)
    from_level = models.ForeignKey(CareerLevel, on_delete=models.PROTECT, related_name="upgrades_from")
    to_level = models.ForeignKey(CareerLevel, on_delete=models.PROTECT, related_name="upgrades_to")
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    period_score = models.ForeignKey(
        "scoring.EmployeePeriodScore", null=True, blank=True, on_delete=models.PROTECT, related_name="upgrades"
    )

    class Meta:
        verbose_name_plural = "Terfiler"

    def clean(self):
        if self.from_level_id == self.to_level_id:
            raise ValidationError(
                "Eski ve yeni seviye aynı olamaz."
            )

        if (
            self.from_level_id
            and self.to_level_id
            and self.to_level.order <= self.from_level.order
        ):
            raise ValidationError(
                "Upgrade yeni seviyeyi daha yüksek bir seviyeye taşımalıdır."
            )


class EmployeeReportingLine(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="reporting_lines")
    manager = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="managed_employees")
    relation_type = models.ForeignKey("ReportingRelationType", on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Personel Raporları"
        ordering = ["employee", "-start_date"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.employee_id == self.manager_id:
            raise ValidationError(
                "Personel kendisinin yöneticisi olamaz."
            )

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )


class ReportingRelationType(TimeStampedModel):
    """
        Şef
        Müdür Yardımcısı
        Müdür
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class EmployeePositionHistory(TimeStampedModel):
    """
    Personel Pozisyon Geçmişi,
    Personel --> Şef,
    Şef --> Müdür Yardımcısı gibi
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="position_history", verbose_name="Personel")
    position = models.ForeignKey(OrganizationPosition, on_delete=models.PROTECT, related_name="employee_history", verbose_name="Pozisyon")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")

    class Meta:
        verbose_name = "Pozisyon Geçmişi"
        verbose_name_plural = "Pozisyon Geçmişleri"
