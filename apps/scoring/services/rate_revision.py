from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.scoring.models import JobLevelRate


class RateRevisionError(Exception):
    pass


class RateRevisionService:

    def __init__(self, revision):
        self.revision = revision
        self.effective_date = revision.effective_date

    # ----------------------------------
    # Revizyon tarihinde geçerli tarifeler
    # ----------------------------------

    def get_source_rates(self):
        """
        Revizyon tarihinden hemen önce geçerli
        olan ücret tarifelerini bulur.

        Örnek:
        Yeni dönem: 01.07.2027

        Kaynak tarife:
        30.06.2027 tarihinde geçerli olan tarife.
        """

        reference_date = self.effective_date - timedelta(days=1)

        return (
            JobLevelRate.objects
            .filter(active=True, valid_from__lte=reference_date)
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=reference_date))
            .select_related("job_role", "level")
            .order_by("job_role__name", "level__order")
        )

    # ----------------------------------
    # Yeni tutarı hesapla
    # ----------------------------------

    def calculate_new_amount(self, old_amount):
        multiplier = Decimal("1") + (self.revision.percentage / Decimal("100"))
        return (old_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ----------------------------------
    # Önizleme
    # ----------------------------------

    def preview(self):
        """
        Veritabanında hiçbir değişiklik yapmaz.
        Sadece eski/yeni tarifeyi hesaplar.
        """
        result = []
        for rate in self.get_source_rates():
            new_amount = self.calculate_new_amount(rate.amount)
            result.append({
                "source_rate": rate,
                "job_role": rate.job_role,
                "level": rate.level,
                "old_amount": rate.amount,
                "new_amount": new_amount,
                "difference":new_amount - rate.amount,
            })

        return result

    # ----------------------------------
    # Kontroller
    # ----------------------------------
    def validate(self):
        if self.revision.applied_at:
            raise RateRevisionError("Bu ücret revizyonu daha önce uygulanmış.")

        source_rates = self.get_source_rates()

        if not source_rates.exists():
            raise RateRevisionError("Revizyon için kullanılabilecek geçerli ücret tarifesi bulunamadı.")

        duplicates = []

        for rate in source_rates:
            exists = (
                JobLevelRate.objects
                .filter(job_role=rate.job_role, level=rate.level, valid_from=self.effective_date)
                .exists()
            )

            if exists:
                duplicates.append(f"{rate.job_role} / {rate.level}")

        if duplicates:
            raise RateRevisionError("Yeni dönem için zaten ücret tarifesi bulunan kayıtlar var: "", ".join(duplicates))

    # ----------------------------------
    # Revizyonu uygula
    # ----------------------------------
    @transaction.atomic
    def apply(self):
        self.validate()
        source_rates = list(self.get_source_rates())
        previous_day = self.effective_date - timedelta(days=1)

        created_rates = []

        for source_rate in source_rates:
            new_amount = self.calculate_new_amount(source_rate.amount)

            # ------------------------------
            # Eski tarifeyi kapat
            # ------------------------------
            source_rate.valid_to = previous_day
            source_rate.save(update_fields=["valid_to", "updated_at"])

            # ------------------------------
            # Yeni tarifeyi oluştur
            # ------------------------------
            new_rate = (
                JobLevelRate.objects.create(
                    job_role=source_rate.job_role,
                    level=source_rate.level,
                    amount=new_amount,
                    valid_from=self.effective_date,
                    valid_to=None,
                    active=True,
                    revision=self.revision,
                )
            )
            created_rates.append(new_rate)

        # ----------------------------------
        # Revizyon uygulandı
        # ----------------------------------
        self.revision.applied_at = timezone.now()
        self.revision.save(update_fields=["applied_at", "updated_at"])

        return created_rates