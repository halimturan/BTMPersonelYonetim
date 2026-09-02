from decimal import Decimal
from django import forms
from apps.performance.models import (PerformanceCriterionScore)
from django.db import transaction
from apps.performance.services.calculator import WeightedReviewerScoreCalculator

class PerformanceReviewForm(forms.Form):

    def __init__(self, *args, reviewer, **kwargs):
        super().__init__(*args, **kwargs)

        self.reviewer = reviewer
        self.evaluation = reviewer.evaluation

        template_items = (
            self.evaluation.template.criteria
            .select_related("criterion")
            .order_by("order")
        )

        existing_scores = {
            item.criterion_id: item
            for item in reviewer.criterion_scores.all()
        }

        for item in template_items:

            field_name = (f"criterion_{item.criterion_id}")
            existing = existing_scores.get(item.criterion_id)

            self.fields[field_name] = (
                forms.DecimalField(
                    label=item.criterion.name,
                    min_value=Decimal("0"),
                    max_value=item.max_score,
                    decimal_places=2,
                    required=item.required,
                    help_text=item.criterion.description,
                    initial=(
                        existing.score
                        if existing
                        else None
                    ),
                )
            )

    @transaction.atomic
    def save(self):

        template_items = (
            self.evaluation.template.criteria
            .select_related("criterion")
            .order_by("order")
        )

        for item in template_items:
            field_name = (
                f"criterion_{item.criterion_id}"
            )

            score = self.cleaned_data[field_name]

            PerformanceCriterionScore.objects.update_or_create(
                reviewer=self.reviewer,
                criterion=item.criterion,
                defaults={
                    "max_score": item.max_score,
                    "score": score,
                },
            )

        raw_score, weighted_score = (
            WeightedReviewerScoreCalculator(
                self.reviewer
            ).calculate()
        )

        self.reviewer.raw_score = raw_score
        self.reviewer.weighted_score = weighted_score

        self.reviewer.save(
            update_fields=[
                "raw_score",
                "weighted_score",
                "updated_at",
            ]
        )

        return self.reviewer


