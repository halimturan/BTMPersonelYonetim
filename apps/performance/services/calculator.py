from decimal import Decimal


class ReviewerPerformanceCalculator:

    def __init__(self, reviewer):
        self.reviewer = reviewer

    def calculate(self):

        scores = (
            self.reviewer
            .criterion_scores
            .all()
        )

        total_score = sum(
            (item.score for item in scores),
            Decimal("0"),
        )

        total_max = sum(
            (item.max_score for item in scores),
            Decimal("0"),
        )

        if total_max == 0:
            return Decimal("0")

        return (
            total_score
            / total_max
            * Decimal("100")
        )

class WeightedReviewerScoreCalculator:

    def __init__(self, reviewer):
        self.reviewer = reviewer

    def calculate(self):
        raw_score = ReviewerPerformanceCalculator(self.reviewer).calculate()
        weighted_score = (raw_score * self.reviewer.weight / Decimal("100"))
        return raw_score, weighted_score