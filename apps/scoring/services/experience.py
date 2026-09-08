import math

from decimal import Decimal

from django.db.models import Q

from apps.scoring.models import ExperienceScoreRule


class ExperienceScoreCalculationError(Exception):
    pass


class ExperienceScoreCalculator:
    def __init__(
        self,
        employee,
        reference_date,
    ):
        self.employee = employee
        self.reference_date = reference_date

    def calculate(self):
        rules = (
            ExperienceScoreRule.objects
            .filter(
                active=True,
                valid_from__lte=self.reference_date,
            )
            .filter(
                Q(valid_to__isnull=True)
                | Q(valid_to__gte=self.reference_date)
            )
            .select_related(
                "experience_source"
            )
        )

        if not rules.exists():
            raise ExperienceScoreCalculationError(
                "Geçerli tecrübe puanlama kuralı bulunamadı."
            )

        if rules.count() > 1:
            raise ExperienceScoreCalculationError(
                (
                    "Aynı tarihte birden fazla aktif "
                    "tecrübe puanlama kuralı bulundu."
                )
            )

        rule = rules.first()

        experience = (
            self.employee.experiences
            .filter(
                source=rule.experience_source,
                start_date__lte=self.reference_date,
            )
            .order_by("start_date")
            .first()
        )

        if not experience:
            raise ExperienceScoreCalculationError(
                (
                    f"{rule.experience_source.name} "
                    "tecrübe kaydı bulunamadı."
                )
            )

        end_date = (
            experience.end_date
            if (
                experience.end_date
                and experience.end_date
                < self.reference_date
            )
            else self.reference_date
        )

        total_days = (
            end_date
            - experience.start_date
        ).days

        if total_days < 0:
            raise ExperienceScoreCalculationError(
                "Tecrübe başlangıç tarihi geçersiz."
            )

        years = Decimal(
            str(total_days / 365.25)
        )

        max_score = Decimal(
            str(rule.max_score)
        )

        decay_factor = Decimal(
            str(rule.decay_factor)
        )

        if decay_factor <= 0:
            raise ExperienceScoreCalculationError(
                "Tecrübe eğrisi katsayısı sıfırdan büyük olmalıdır."
            )

        score = max_score * (
            Decimal("1")
            - Decimal(
                str(
                    math.exp(
                        -float(
                            years / decay_factor
                        )
                    )
                )
            )
        )

        return score.quantize(
            Decimal("0.0001")
        )