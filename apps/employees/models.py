from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from django.db.models import Q
from apps.organization.models import (CareerLevel, Department, EmploymentType, JobRole, JobTitle, Unit)
from apps.employees.services.personnel_detais import get_ibb_user_info


class Employee(TimeStampedModel):
    gender_choices = (
        ("kadin", "Kadın"),
        ("erkek", "Erkek"),
    )
    personnel_no = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Sicil No", null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Ad", null=True, blank=True)
    last_name = models.CharField(max_length=100, verbose_name="Soyad", null=True, blank=True)
    gender = models.CharField(max_length=20, verbose_name="Cinsiyet", choices=gender_choices)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, related_name="employees", verbose_name="Personel Tipi")
    domain_name = models.CharField(max_length=100, verbose_name="Domain Adı", help_text="Ör: adem.karakaya")
    phone = models.BigIntegerField(verbose_name="Telefon", null=True, blank=True)

    current_management_level = models.ForeignKey("organization.ManagementLevel", on_delete=models.PROTECT,
                                                 related_name="employees", null=True, blank=True,
                                                 verbose_name="Yönetim Seviyesi")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    def save(self, *args, **kwargs):
        if self.domain_name:
            user_info = get_ibb_user_info(self.domain_name)
            self.first_name = user_info.get('ad')
            self.last_name = user_info.get('soyad')
            self.phone = user_info.get('cepTelefonu')
            self.personnel_no = user_info.get('kurumSicilNo')
        super(Employee, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Personel"
        verbose_name_plural = "Personeller"
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["personnel_no"]),
            models.Index(fields=["is_active"]),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.personnel_no} - {self.full_name}"

    @property
    def current_department_record(self):
        today = timezone.localdate()

        return (
            self.department_history
            .filter(start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .select_related("department", "unit")
            .order_by("-start_date")
            .first()
        )

    @property
    def current_department(self):
        record = self.current_department_record
        return record.department if record else None

    @property
    def current_unit(self):
        record = self.current_department_record
        return record.unit if record else None

    @property
    def current_title_record(self):
        today = timezone.localdate()

        return (
            self.title_history
            .filter(start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .select_related("job_title",)
            .order_by("-start_date")
            .first()
        )

    @property
    def current_title(self):
        record = self.current_title_record
        return record.job_title if record else None

    @property
    def current_assignment(self):
        today = timezone.localdate()

        return (
            self.assignments
            .filter(start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .select_related("job_role")
            .order_by("-start_date")
            .first()
        )

    @property
    def current_job_role(self):
        assignment = self.current_assignment
        return assignment.job_role if assignment else None

    @property
    def current_level_record(self):
        today = timezone.localdate()

        return (
            self.level_history
            .filter(start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .select_related("job_role", "level")
            .order_by("-start_date")
            .first()
        )


class EducationLevel(TimeStampedModel):
    name = models.CharField(max_length=100, verbose_name="İsim")
    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    order = models.PositiveIntegerField(default=0, verbose_name="Sıra")
    active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    class Meta:
        verbose_name_plural = "Mezuniyetler"
        ordering = ["order"]

    def __str__(self):
        return self.name


class EmployeeEducation(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="educations", verbose_name="Personel")
    education_level = models.ForeignKey(EducationLevel, on_delete=models.PROTECT, verbose_name="Eğitim Seviyesi")
    school_name = models.CharField(max_length=250, blank=True, verbose_name="Okul Adı")
    department_name = models.CharField(max_length=250, blank=True, verbose_name="Bölüm")
    graduation_date = models.DateField(null=True, blank=True, verbose_name="Mezuniyet Tarihi")
    is_it_related = models.BooleanField(default=False)
    is_engineering = models.BooleanField(default=False)
    is_open_education = models.BooleanField(default=False)

    is_primary_for_scoring = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Personel - Mezuniyet"
        ordering = ["employee", "-is_primary_for_scoring", "-graduation_date"]

    def clean(self):
        if not self.is_primary_for_scoring:
            return

        exists = (
            EmployeeEducation.objects
            .filter(employee=self.employee, is_primary_for_scoring=True)
            .exclude(pk=self.pk)
            .exists()
        )

        if exists:
            raise ValidationError(
                "Bir personelin puanlamada kullanılan "
                "yalnızca bir aktif mezuniyeti olabilir."
            )


def validate_history_overlap(model, employee, start_date, end_date, instance_pk=None):
    qs = model.objects.filter(employee=employee)

    if instance_pk:
        qs = qs.exclude(pk=instance_pk)

    if end_date:
        qs = qs.filter(start_date__lte=end_date)

    qs = qs.filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=start_date))

    if qs.exists():
        raise ValidationError(
            "Bu personel için tarih aralığı mevcut "
            "bir kayıtla çakışıyor."
        )


class EmployeeAssignmentHistory(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="assignments", verbose_name="Personel")
    job_role = models.ForeignKey(JobRole, on_delete=models.PROTECT, verbose_name="İş Kolu")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")
    description = models.TextField(blank=True, verbose_name="Açıklama")

    class Meta:
        verbose_name_plural = "Atama Geçmişi"
        ordering = ["employee", "-start_date"]
        indexes = [
            models.Index(fields=["employee", "start_date", "end_date"])
        ]

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        validate_history_overlap(EmployeeAssignmentHistory, self.employee, self.start_date, self.end_date, self.pk)

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

        validate_history_overlap(EmployeeTitleHistory, self.employee, self.start_date, self.end_date, self.pk)

    def __str__(self):
        return f"{self.employee} - {self.job_title}"


class EmployeeDepartmentHistory(TimeStampedModel):
    """
    Departman/Birim Geçmişi
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="department_history", verbose_name="Personel")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="Müdür Yardımcılığı")
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, verbose_name="Şeflik")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")

    class Meta:
        verbose_name = "Şeflik Değişimi Geçmişi"
        verbose_name_plural = "Şeflik Değşimi Geçmişi"
        ordering = ["employee", "-start_date"]

    def clean(self):
        super().clean()

        level = self.employee.current_management_level

        if not level:
            return

        if level.code == "PERSONNEL" and not self.unit_id:
            raise ValidationError("Personel mutlaka bir şefliğe bağlı olmalıdır.")

        if level.code == "CHIEF" and not self.unit_id:
            raise ValidationError("Şef mutlaka bir şeflik birimine bağlı olmalıdır.")

        validate_history_overlap(EmployeeDepartmentHistory, self.employee, self.start_date, self.end_date, self.pk)


class EmployeeLevelHistory(TimeStampedModel):
    """
    Seviye Geçmişi
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="level_history")
    job_role = models.ForeignKey(JobRole, on_delete=models.PROTECT)
    level = models.ForeignKey(CareerLevel, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Seviye Geçmişi"
        ordering = ["employee", "-start_date"]

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        validate_history_overlap(EmployeeLevelHistory, self.employee, self.start_date, self.end_date, self.pk,)


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


class EmployeeExperience(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="experiences", verbose_name="Personel")
    source = models.ForeignKey("scoring.ExperienceSource", on_delete=models.PROTECT, related_name="employee_experiences", verbose_name="Kaynak")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")
    description = models.TextField(blank=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Personel Deneyimi"
        verbose_name_plural = "Personel Deneyimleri"
        ordering = ["-start_date"]

    def clean(self):
        super().clean()

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "Bitiş tarihi başlangıç tarihinden önce olamaz."
            })


class EmployeeManagementLevelHistory(TimeStampedModel):
    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="management_level_history", verbose_name="Personel")
    management_level = models.ForeignKey("organization.ManagementLevel", on_delete=models.PROTECT, related_name="employee_history", verbose_name="Yönetsel Seviye")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")

    class Meta:
        verbose_name = "Personel Yönetsel Seviye Geçmişi"
        verbose_name_plural = "Personel Yönetsel Seviye Geçmişi"
        ordering = ["-start_date", "-pk"]

    def __str__(self):
        return f"{self.employee} - {self.management_level}"
