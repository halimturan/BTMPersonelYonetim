from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.performance.models import PerformanceCriterionScore
from apps.performance.services.calculator import ReviewerPerformanceCalculator, WeightedReviewerScoreCalculator
from apps.performance.services.evaluation_completion import EvaluationCompletionService


class ReviewSubmissionError(Exception):
    pass


class ReviewSubmissionService:
    def __init__(self, reviewer):
        self.reviewer = reviewer

    def _template_items(self):
        return (
            self.reviewer
            .evaluation
            .template
            .criteria
            .select_related("criterion")
            .order_by("order")
        )

    @transaction.atomic
    def save_draft(self, cleaned_data):
        if self.reviewer.submitted_at:
            raise ReviewSubmissionError(
                "Gönderilmiş değerlendirme değiştirilemez."
            )

        for item in self._template_items():
            criterion = item.criterion

            score_key = (
                f"criterion_{criterion.pk}"
            )

            comment_key = (
                f"comment_{criterion.pk}"
            )

            score = cleaned_data.get(
                score_key
            )

            comment = cleaned_data.get(
                comment_key,
                "",
            )

            if score is None:
                continue

            PerformanceCriterionScore.objects.update_or_create(
                reviewer=self.reviewer,
                criterion=criterion,
                defaults={
                    "max_score": item.max_score,
                    "score": score,
                    "comment": comment,
                },
            )

        self._recalculate()

    @transaction.atomic
    def submit(self, cleaned_data):
        if self.reviewer.submitted_at:
            raise ReviewSubmissionError(
                "Bu değerlendirme daha önce gönderilmiş."
            )

        self.save_draft(cleaned_data)

        missing = self.get_missing_required_criteria()

        if missing:
            names = ", ".join(
                criterion.name
                for criterion in missing
            )

            raise ReviewSubmissionError(
                "Zorunlu kriterler tamamlanmadı: "
                f"{names}"
            )

        self._recalculate()

        self.reviewer.submitted_at = (
            timezone.now()
        )

        self.reviewer.save(
            update_fields=[
                "raw_score",
                "weighted_score",
                "submitted_at",
                "updated_at",
            ]
        )

        EvaluationCompletionService(
            self.reviewer.evaluation
        ).complete_if_ready()

    def get_missing_required_criteria(self):
        required_items = (
            self._template_items()
            .filter(required=True)
        )

        scored_ids = set(
            self.reviewer
            .criterion_scores
            .values_list(
                "criterion_id",
                flat=True,
            )
        )

        return [
            item.criterion
            for item in required_items
            if item.criterion_id
            not in scored_ids
        ]

    def _recalculate(self):
        raw_score = (
            ReviewerPerformanceCalculator(
                self.reviewer
            ).calculate()
        )

        weighted_score = (
            WeightedReviewerScoreCalculator(
                self.reviewer
            ).calculate(
                raw_score
            )
        )

        self.reviewer.raw_score = raw_score
        self.reviewer.weighted_score = (
            weighted_score
        )

        self.reviewer.save(
            update_fields=[
                "raw_score",
                "weighted_score",
                "updated_at",
            ]
        )