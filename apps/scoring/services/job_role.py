from decimal import Decimal
from django.db.models import Q
from apps.scoring.models import JobRoleScoreRule


class JobRoleScoreCalculationError(Exception):
    pass


class JobRoleScoreCalculator:
    def __init__(
        self,
        job_role,
        reference_date,
    ):
        self.job_role = job_role
        self.reference_date = reference_date

    def calculate(self):
        if not self.job_role:
            raise JobRoleScoreCalculationError(
                "Personelin dönem için iş kolu bulunamadı."
            )

        rules = (
            JobRoleScoreRule.objects
            .filter(
                active=True,
                job_role=self.job_role,
                valid_from__lte=self.reference_date,
            )
            .filter(
                Q(valid_to__isnull=True)
                | Q(valid_to__gte=self.reference_date)
            )
        )

        if not rules.exists():
            raise JobRoleScoreCalculationError(
                (
                    f"{self.job_role} için "
                    "iş kolu puanlama kuralı bulunamadı."
                )
            )

        if rules.count() > 1:
            raise JobRoleScoreCalculationError(
                (
                    f"{self.job_role} için aynı tarihte "
                    "birden fazla aktif puanlama kuralı bulundu."
                )
            )

        return Decimal(
            str(rules.first().score)
        )