from datetime import timedelta
from decimal import Decimal

from django.db.models import Q

from apps.scoring.models import JobLevelRate


class EmployeeCompensationService:

    def __init__(self, employee):
        self.employee = employee

    def _get_rate(
        self,
        job_role,
        level,
        reference_date,
    ):
        if not job_role or not level:
            return None

        return (
            JobLevelRate.objects
            .filter(
                job_role=job_role,
                level=level,
                active=True,
                valid_from__lte=reference_date,
            )
            .filter(
                Q(valid_to__isnull=True)
                | Q(valid_to__gte=reference_date)
            )
            .order_by(
                "-valid_from",
                "-pk",
            )
            .first()
        )

    def get_history(self):
        events = []

        # ==================================
        # 1. GENEL ÜCRET ZAMLARI
        # ==================================

        level_records = (
            self.employee.level_history
            .select_related(
                "job_role",
                "level",
            )
            .order_by(
                "start_date",
                "pk",
            )
        )

        for level_record in level_records:

            rates = (
                JobLevelRate.objects
                .filter(
                    job_role=level_record.job_role,
                    level=level_record.level,
                    active=True,
                )
                .order_by(
                    "valid_from",
                    "pk",
                )
            )

            for rate in rates:

                # Tarife başlangıcı personelin
                # bu iş kolu / seviyede bulunduğu
                # döneme denk gelmeli.

                if (
                    rate.valid_from
                    < level_record.start_date
                ):
                    continue

                if (
                    level_record.end_date
                    and rate.valid_from
                    > level_record.end_date
                ):
                    continue

                previous_date = (
                    rate.valid_from
                    - timedelta(days=1)
                )

                previous_rate = self._get_rate(
                    level_record.job_role,
                    level_record.level,
                    previous_date,
                )

                if not previous_rate:
                    continue

                if (
                    previous_rate.amount
                    == rate.amount
                ):
                    continue

                percentage = None

                if previous_rate.amount:
                    percentage = (
                        (
                            rate.amount
                            - previous_rate.amount
                        )
                        / previous_rate.amount
                        * Decimal("100")
                    ).quantize(
                        Decimal("0.01")
                    )

                events.append({
                    "date":
                        rate.valid_from,

                    "type":
                        "GENERAL_RAISE",

                    "type_label":
                        "Genel Zam",

                    "from_job_role":
                        level_record.job_role,

                    "to_job_role":
                        level_record.job_role,

                    "from_level":
                        level_record.level,

                    "to_level":
                        level_record.level,

                    "old_amount":
                        previous_rate.amount,

                    "new_amount":
                        rate.amount,

                    "percentage":
                        percentage,

                    "revision":
                        getattr(
                            rate,
                            "revision",
                            None,
                        ),
                })

        # ==================================
        # 2. UPGRADE / İŞ KOLU DEĞİŞİKLİĞİ
        # ==================================

        upgrades = (
            self.employee.upgrades
            .select_related(
                "from_job_role",
                "to_job_role",
                "from_level",
                "to_level",
            )
            .order_by(
                "effective_date",
                "pk",
            )
        )

        for upgrade in upgrades:

            # ------------------------------
            # ESKİ ÜCRET
            #
            # Eski iş kolu + eski seviye
            # ------------------------------

            old_rate = self._get_rate(
                upgrade.from_job_role,
                upgrade.from_level,
                upgrade.effective_date,
            )

            # ------------------------------
            # YENİ ÜCRET
            #
            # Yeni iş kolu + yeni seviye
            # ------------------------------

            new_rate = self._get_rate(
                upgrade.to_job_role,
                upgrade.to_level,
                upgrade.effective_date,
            )

            if (
                not old_rate
                or not new_rate
            ):
                continue

            percentage = None

            if old_rate.amount:
                percentage = (
                    (
                        new_rate.amount
                        - old_rate.amount
                    )
                    / old_rate.amount
                    * Decimal("100")
                ).quantize(
                    Decimal("0.01")
                )

            # ------------------------------
            # Hareket tipi
            # ------------------------------

            job_role_changed = (
                upgrade.from_job_role_id
                != upgrade.to_job_role_id
            )

            if job_role_changed:
                type_label = (
                    "İş Kolu / Seviye Değişikliği"
                )
            else:
                type_label = "Upgrade"

            events.append({
                "date":
                    upgrade.effective_date,

                "type":
                    "UPGRADE",

                "type_label":
                    type_label,

                "from_job_role":
                    upgrade.from_job_role,

                "to_job_role":
                    upgrade.to_job_role,

                "from_level":
                    upgrade.from_level,

                "to_level":
                    upgrade.to_level,

                "old_amount":
                    old_rate.amount,

                "new_amount":
                    new_rate.amount,

                "percentage":
                    percentage,

                "revision":
                    None,
            })

        # ==================================
        # En yeni hareket en üstte
        # ==================================

        events.sort(
            key=lambda item: item["date"],
            reverse=True,
        )

        return events