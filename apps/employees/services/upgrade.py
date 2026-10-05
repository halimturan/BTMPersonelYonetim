from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from apps.employees.models import EmployeeAssignmentHistory, EmployeeLevelHistory


class EmployeeUpgradeError(Exception):
    pass


class EmployeeUpgradeService:
    """
    Personelin kariyer hareketini uygular.

    Örnek 1:
        Yazılım Geliştirici / Orta
        ->
        Yazılım Geliştirici / İleri

        Sadece seviye geçmişi değişir.

    Örnek 2:
        Yazılım Geliştirici / İleri
        ->
        Şef / Başlangıç

        Hem iş kolu geçmişi
        hem seviye geçmişi değişir.
    """

    def __init__(self, upgrade):
        self.upgrade = upgrade
        self.employee = upgrade.employee
        self.effective_date = (
            upgrade.effective_date
        )

    # ==========================================
    # YÜRÜRLÜK TARİHİNDEKİ İŞ KOLU
    # ==========================================

    def get_assignment_record(self):
        """
        Upgrade yürürlük tarihinde geçerli
        iş kolu kaydını döndürür.
        """

        return (
            self.employee.assignments
            .filter(
                start_date__lte=
                    self.effective_date,
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=
                        self.effective_date
                )
            )
            .select_related(
                "job_role",
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

    # ==========================================
    # YÜRÜRLÜK TARİHİNDEKİ SEVİYE
    # ==========================================

    def get_level_record(self):
        """
        Upgrade yürürlük tarihinde geçerli
        kariyer seviyesi kaydını döndürür.
        """

        return (
            self.employee.level_history
            .filter(
                start_date__lte=
                    self.effective_date,
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=
                        self.effective_date
                )
            )
            .select_related(
                "job_role",
                "level",
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

    # ==========================================
    # VALIDATION
    # ==========================================

    def validate(
        self,
        assignment_record,
        level_record,
    ):
        """
        Upgrade'ın mevcut organizasyon/kariyer
        kayıtlarıyla uyumlu olduğunu kontrol eder.
        """

        if not assignment_record:
            raise EmployeeUpgradeError(
                (
                    f"{self.employee.full_name} için "
                    f"{self.effective_date:%d.%m.%Y} "
                    "tarihinde geçerli iş kolu "
                    "kaydı bulunamadı."
                )
            )

        if not level_record:
            raise EmployeeUpgradeError(
                (
                    f"{self.employee.full_name} için "
                    f"{self.effective_date:%d.%m.%Y} "
                    "tarihinde geçerli kariyer "
                    "seviyesi bulunamadı."
                )
            )

        # --------------------------------------
        # Assignment ile level history
        # birbirini tutuyor mu?
        # --------------------------------------

        if (
            assignment_record.job_role_id
            != level_record.job_role_id
        ):
            raise EmployeeUpgradeError(
                (
                    "Personelin iş kolu kaydı ile "
                    "kariyer seviye kaydı birbiriyle "
                    "uyuşmuyor. "
                    f"İş kolu: "
                    f"{assignment_record.job_role}, "
                    f"seviye kaydındaki iş kolu: "
                    f"{level_record.job_role}."
                )
            )

        # --------------------------------------
        # Upgrade'ın eski iş kolu doğru mu?
        # --------------------------------------

        if (
            assignment_record.job_role_id
            != self.upgrade.from_job_role_id
        ):
            raise EmployeeUpgradeError(
                (
                    "Upgrade eski iş kolu personelin "
                    "yürürlük tarihindeki iş koluyla "
                    "uyuşmuyor. "
                    f"Mevcut: "
                    f"{assignment_record.job_role}, "
                    f"Upgrade: "
                    f"{self.upgrade.from_job_role}."
                )
            )

        # --------------------------------------
        # Upgrade'ın eski seviyesi doğru mu?
        # --------------------------------------

        if (
            level_record.level_id
            != self.upgrade.from_level_id
        ):
            raise EmployeeUpgradeError(
                (
                    "Upgrade eski seviyesi personelin "
                    "yürürlük tarihindeki seviyesiyle "
                    "uyuşmuyor. "
                    f"Mevcut: "
                    f"{level_record.level}, "
                    f"Upgrade: "
                    f"{self.upgrade.from_level}."
                )
            )

        # --------------------------------------
        # Hiçbir şey değişmiyorsa upgrade değil
        # --------------------------------------

        same_job_role = (
            self.upgrade.from_job_role_id
            == self.upgrade.to_job_role_id
        )

        same_level = (
            self.upgrade.from_level_id
            == self.upgrade.to_level_id
        )

        if same_job_role and same_level:
            raise EmployeeUpgradeError(
                (
                    "Upgrade sonucunda iş kolu veya "
                    "kariyer seviyesi değişmelidir."
                )
            )

        # --------------------------------------
        # Aynı iş kolunda upgrade yapılıyorsa
        # yeni seviye daha yüksek olmalı.
        #
        # İş kolu değişiyorsa bu kontrol YOK.
        #
        # Örn:
        # Yazılım Geliştirici / İleri
        # -> Şef / Başlangıç
        # geçerlidir.
        # --------------------------------------

        if same_job_role:
            if (
                self.upgrade.to_level.order
                <= self.upgrade.from_level.order
            ):
                raise EmployeeUpgradeError(
                    (
                        "Aynı iş kolundaki upgrade "
                        "işleminde yeni kariyer seviyesi "
                        "mevcut seviyeden daha yüksek "
                        "olmalıdır."
                    )
                )

    # ==========================================
    # MÜKERRER KAYIT KONTROLLERİ
    # ==========================================

    def validate_target_records(self):
        """
        Aynı başlangıç tarihinde aynı hedef
        kayıtların zaten bulunmasını engeller.
        """

        level_exists = (
            self.employee.level_history
            .filter(
                job_role=
                    self.upgrade.to_job_role,
                level=
                    self.upgrade.to_level,
                start_date=
                    self.effective_date,
            )
            .exists()
        )

        if level_exists:
            raise EmployeeUpgradeError(
                (
                    "Bu personel için aynı tarihte "
                    "aynı iş kolu ve kariyer seviyesine "
                    "ait kayıt zaten bulunuyor."
                )
            )

        job_role_changed = (
            self.upgrade.from_job_role_id
            != self.upgrade.to_job_role_id
        )

        if job_role_changed:

            assignment_exists = (
                self.employee.assignments
                .filter(
                    job_role=
                        self.upgrade.to_job_role,
                    start_date=
                        self.effective_date,
                )
                .exists()
            )

            if assignment_exists:
                raise EmployeeUpgradeError(
                    (
                        "Bu personel için aynı tarihte "
                        "hedef iş koluna ait görev "
                        "kaydı zaten bulunuyor."
                    )
                )

    # ==========================================
    # APPLY
    # ==========================================

    @transaction.atomic
    def apply(self):
        """
        Upgrade işlemini uygular.

        İş kolu değişiyorsa:
            - eski assignment kapanır
            - yeni assignment açılır

        Her durumda:
            - eski level history kapanır
            - yeni level history açılır
        """

        # Aynı anda başka işlem değişiklik
        # yapmasın diye kayıtları kilitleyelim.

        assignment_record = (
            self.employee.assignments
            .select_for_update()
            .filter(
                start_date__lte=
                    self.effective_date,
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=
                        self.effective_date
                )
            )
            .select_related(
                "job_role",
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

        level_record = (
            self.employee.level_history
            .select_for_update()
            .filter(
                start_date__lte=
                    self.effective_date,
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=
                        self.effective_date
                )
            )
            .select_related(
                "job_role",
                "level",
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

        # --------------------------------------
        # Kontroller
        # --------------------------------------

        self.validate(
            assignment_record,
            level_record,
        )

        self.validate_target_records()

        previous_day = (
            self.effective_date
            - timedelta(days=1)
        )

        job_role_changed = (
            self.upgrade.from_job_role_id
            != self.upgrade.to_job_role_id
        )

        # ======================================
        # 1. İŞ KOLU DEĞİŞİMİ
        # ======================================

        new_assignment = None

        if job_role_changed:

            # Eski iş kolunu kapat

            assignment_record.end_date = (
                previous_day
            )

            assignment_record.save(
                update_fields=[
                    "end_date",
                    "updated_at",
                ]
            )

            # Yeni iş kolunu aç

            new_assignment = (
                EmployeeAssignmentHistory.objects.create(
                    employee=self.employee,
                    job_role=
                        self.upgrade.to_job_role,
                    start_date=
                        self.effective_date,
                    end_date=None,
                )
            )

        # ======================================
        # 2. ESKİ SEVİYEYİ KAPAT
        # ======================================

        level_record.end_date = previous_day

        level_record.save(
            update_fields=[
                "end_date",
                "updated_at",
            ]
        )

        # ======================================
        # 3. YENİ SEVİYEYİ AÇ
        # ======================================

        new_level_record = (
            EmployeeLevelHistory.objects.create(
                employee=self.employee,
                job_role=
                    self.upgrade.to_job_role,
                level=
                    self.upgrade.to_level,
                start_date=
                    self.effective_date,
                end_date=None,
            )
        )

        return {
            "assignment":
                new_assignment,

            "level_record":
                new_level_record,

            "job_role_changed":
                job_role_changed,
        }