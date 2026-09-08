from decimal import Decimal
from django.db import models
from apps.performance.models import PerformanceEvaluation


class PerformanceScoreCalculationError(Exception):
    pass


class PerformanceScoreCalculator:
    def __init__(
        self,
        employee,
        period,
    ):
        self.employee = employee
        self.period = period

    def calculate(self):
        evaluation = (
            PerformanceEvaluation.objects
            .filter(
                employee=self.employee,
                period=self.period,
            )
            .first()
        )

        if not evaluation:
            raise PerformanceScoreCalculationError(
                "Personel için performans değerlendirmesi bulunamadı."
            )

        if evaluation.completed_at is None:
            raise PerformanceScoreCalculationError(
                "Performans değerlendirmesi henüz tamamlanmadı."
            )

        if evaluation.final_performance_score is None:
            raise PerformanceScoreCalculationError(
                "Performans skoru hesaplanmamış."
            )

        return Decimal(
            str(
                evaluation.final_performance_score
            )
        )

    def get_assignment_record(
            self,
            employee,
    ):
        return (
            employee.assignments
            .filter(
                start_date__lte=self.reference_date,
            )
            .filter(
                models.Q(end_date__isnull=True)
                | models.Q(
                    end_date__gte=self.reference_date
                )
            )
            .select_related(
                "job_role"
            )
            .order_by("-start_date")
            .first()
        )

    def get_job_role(self, employee):
        record = self.get_assignment_record(
            employee
        )

        return (
            record.job_role
            if record
            else None
        )