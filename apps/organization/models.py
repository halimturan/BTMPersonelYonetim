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
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="units", verbose_name="Müdür Yardımcılığı")
    name = models.CharField(max_length=150, verbose_name="İsim")
    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    class Meta:
        ordering = ["department__name", "name"]
        verbose_name = "Şeflik"
        verbose_name_plural = "Şeflikler"

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


class ManagementLevel(TimeStampedModel):
    """
    Organizasyon hiyerarşisindeki yönetsel seviye.

    Örnek:
        Personel             order=10
        Şef                  order=20
        Müdür Yardımcısı     order=30
        Müdür                order=40
    """
    name = models.CharField(max_length=100, verbose_name="İsim")
    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    order = models.PositiveIntegerField(default=0, verbose_name="Ağırlık")
    can_manage_people = models.BooleanField(default=False, verbose_name="Sistemde işlem yapabilir mi?")
    active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    class Meta:
        verbose_name = "Yönetsel Seviye"
        verbose_name_plural = "Yönetse Seviyeler"
        ordering = ["order"]

    def __str__(self):
        return self.name


class JobTitle(TimeStampedModel):
    """
    Resmî unvan.

    Örnek:
        Memur
        Mühendis
        Tekniker
        Şef
        Kıdemli Şef
        Müdür Yardımcısı
        Müdür
    """
    name = models.CharField(max_length=150)
    management_level = models.ForeignKey(ManagementLevel, null=True, blank=True, on_delete=models.PROTECT, related_name="job_titles")
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
    Personelin yaptığı iş.

    Örnek:
        Yazılım Geliştirici
        İş Analisti
        Sistem Yöneticisi
        Teknik Servis
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
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
