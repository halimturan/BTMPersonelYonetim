from decimal import Decimal
from apps.performance.models import (PerformanceCriterionScore)
from django.db import transaction
from apps.performance.services.calculator import WeightedReviewerScoreCalculator
from django import forms
from apps.performance.models import EvaluationPeriod


class PerformanceReviewForm(forms.Form):
    def __init__(
        self,
        *args,
        reviewer=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.reviewer = reviewer
        self.template_criteria = []

        if not reviewer:
            return

        evaluation = reviewer.evaluation
        template = evaluation.template

        self.template_criteria = list(
            template.criteria
            .select_related("criterion")
            .order_by("order", "pk")
        )

        existing_scores = {
            score.criterion_id: score
            for score in reviewer.criterion_scores.all()
        }

        is_submitted = bool(
            reviewer.submitted_at
        )

        for item in self.template_criteria:
            criterion = item.criterion

            score_field_name = (
                f"score_{criterion.pk}"
            )

            comment_field_name = (
                f"comment_{criterion.pk}"
            )

            existing = existing_scores.get(
                criterion.pk
            )

            #
            # PUAN
            #
            self.fields[score_field_name] = (
                forms.DecimalField(
                    label=criterion.name,
                    required=False,
                    min_value=0,
                    max_value=item.max_score,
                    decimal_places=2,
                    max_digits=5,
                    initial=(
                        existing.score
                        if existing
                        else None
                    ),
                    disabled=is_submitted,
                    widget=forms.NumberInput(
                        attrs={
                            "class": (
                                "form-control "
                                "score-input"
                            ),
                            "step": "0.5",
                            "min": "0",
                            "max": str(
                                item.max_score
                            ),
                            "data-max-score": str(
                                item.max_score
                            ),
                            "placeholder": (
                                f"0 - "
                                f"{item.max_score}"
                            ),
                        }
                    ),
                )
            )

            #
            # AÇIKLAMA
            #
            self.fields[comment_field_name] = (
                forms.CharField(
                    label="Açıklama",
                    required=False,
                    initial=(
                        existing.comment
                        if existing
                        else ""
                    ),
                    disabled=is_submitted,
                    widget=forms.Textarea(
                        attrs={
                            "class": "form-control",
                            "rows": 3,
                            "placeholder": (
                                "Değerlendirme ile "
                                "ilgili açıklama..."
                            ),
                        }
                    ),
                )
            )

    def get_criterion_rows(self):
        rows = []

        for item in self.template_criteria:
            criterion = item.criterion

            score_field_name = (
                f"score_{criterion.pk}"
            )

            comment_field_name = (
                f"comment_{criterion.pk}"
            )

            rows.append({
                "item": item,
                "criterion": criterion,

                "score_field":
                    self[score_field_name],

                "comment_field":
                    self[comment_field_name],
            })

        return rows



class EvaluationPeriodForm(forms.ModelForm):
    class Meta:
        model = EvaluationPeriod

        fields = (
            "name",
            "start_date",
            "end_date",
            "evaluation_start_date",
            "evaluation_end_date",
        )

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Örn. 2026 / 2",
                }
            ),

            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "evaluation_start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "evaluation_end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get(
            "start_date"
        )

        end_date = cleaned_data.get(
            "end_date"
        )

        evaluation_start_date = (
            cleaned_data.get(
                "evaluation_start_date"
            )
        )

        evaluation_end_date = (
            cleaned_data.get(
                "evaluation_end_date"
            )
        )

        if (
            start_date
            and end_date
            and start_date >= end_date
        ):
            self.add_error(
                "end_date",
                (
                    "Dönem bitiş tarihi başlangıç "
                    "tarihinden sonra olmalıdır."
                ),
            )

        if (
            evaluation_start_date
            and evaluation_end_date
            and evaluation_start_date
            >= evaluation_end_date
        ):
            self.add_error(
                "evaluation_end_date",
                (
                    "Değerlendirme bitiş tarihi "
                    "başlangıç tarihinden sonra olmalıdır."
                ),
            )

        return cleaned_data


