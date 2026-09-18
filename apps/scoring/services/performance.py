from decimal import Decimal
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
