from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import TimeStampedModel


class Department(TimeStampedModel):
    """
    Müdür Yardımcılıkların tutulduğu modeldir.
    Müdür Yardımcılığı 1, Müdür Yardımcılığı 2 vb.
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Departman"
        verbose_name_plural = "Departmanlar"

    def __str__(self):
        return self.name


class Unit(TimeStampedModel):
    """
    Şefliklerin veya alt birimlerin tutulduğu modeldir.
    PHP, .NET, JAVA, FRONT END, SİSTEM, VERİTABANI vb.
    """
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="units",
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["department__name", "name"]
        verbose_name = "Şeflik"
        verbose_name_plural = "Şeflikler"

    def clean(self):
        if self.parent and self.parent.department_id != self.department_id:
            raise ValidationError(
                "Üst birim ile alt birim aynı departmanda olmalıdır."
            )

        if self.parent_id == self.id:
            raise ValidationError(
                "Bir birim kendisinin üst birimi olamaz."
            )

    def __str__(self):
        return self.name


class EmploymentType(TimeStampedModel):
    """
    Personel tipi. Memur, işçi, Sözleşmeli, Şirket Personeli gibi
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Personel Tipi"
        verbose_name_plural = "Personel Tipleri"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobTitle(TimeStampedModel):
    """
    Resmi unvan:
    Memur, Mühendis, Şef, Kıdemli Şef vb.
    """

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Resmi Ünvan"
        verbose_name_plural = "Resmi Ünvanlar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobRole(TimeStampedModel):
    """
    Fiili görev:
    Yazılım Geliştirici,
    DevOps Yöneticisi,
    Sistem Yöneticisi vb.
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)

    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT, related_name="job_roles")
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "İş Kolları"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CareerLevel(TimeStampedModel):
    """
    Başlangıç / Orta / İleri gibi seviyeler.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField()
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Kariyer Seviyeleri"
        ordering = ["order"]

    def __str__(self):
        return self.name
