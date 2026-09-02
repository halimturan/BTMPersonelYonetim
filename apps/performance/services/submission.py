from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.performance.services.calculator import WeightedReviewerScoreCalculator


class ReviewSubmissionService:

    def __init__(self, reviewer):
        self.reviewer = reviewer

    def submit(self):

        if self.reviewer.submitted_at:
            raise ValidationError(
                "Bu değerlendirme daha önce gönderilmiş."
            )

        required_criteria = (
            self.reviewer
            .evaluation
            .template
            .criteria
            .filter(required=True)
            .count()
        )

        completed = (
            self.reviewer
            .criterion_scores
            .count()
        )

        if completed < required_criteria:
            raise ValidationError(
                "Tüm zorunlu performans kriterleri "
                "puanlanmadan değerlendirme gönderilemez."
            )

        raw_score, weighted_score = (
            WeightedReviewerScoreCalculator(
                self.reviewer
            ).calculate()
        )

        self.reviewer.raw_score = raw_score
        self.reviewer.weighted_score = weighted_score
        self.reviewer.submitted_at = timezone.now()

        self.reviewer.save()