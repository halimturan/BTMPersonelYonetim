from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from apps.scoring.services.final_score import  EmployeeFinalScoreCalculator, FinalScoreCalculationError

class EvaluationCompletionService:
    def __init__(self, evaluation):
        self.evaluation = evaluation

    @transaction.atomic
    def complete_if_ready(self):
        reviewers = list(
            self.evaluation.reviewers.all()
        )

        if not reviewers:
            return False

        if any(
            reviewer.submitted_at is None
            for reviewer in reviewers
        ):
            return False

        final_score = sum(
            (
                reviewer.weighted_score
                or Decimal("0")
            )
            for reviewer in reviewers
        )

        self.evaluation.final_performance_score = (
            final_score
        )

        self.evaluation.completed_at = timezone.now()

        self.evaluation.save(
            update_fields=[
                "final_performance_score",
                "completed_at",
                "updated_at",
            ]
        )

        try:
            EmployeeFinalScoreCalculator(
                employee=self.evaluation.employee,
                period=self.evaluation.period,
            ).calculate_and_save()

        except FinalScoreCalculationError:
            pass

        return True