from django.db.models import Count, Q
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.performance.models import EvaluationPeriod
from apps.scoring.models import EmployeePeriodScore


class EvaluationPeriodDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = EvaluationPeriod
    template_name = "performance/period_detail.html"
    context_object_name = "period"
    permission_required = "performance.view_evaluationperiod"

    def get_queryset(self):
        return (
            EvaluationPeriod.objects
            .annotate(
                evaluation_count=Count("evaluations", distinct=True),
                completed_count=Count(
                    "evaluations",
                    filter=Q(evaluations__completed_at__isnull=False),
                    distinct=True,
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.object

        evaluations = (
            period.evaluations
            .select_related("employee", "status", "template")
            .prefetch_related("reviewers")
            .order_by("employee__first_name", "employee__last_name")
        )

        context["evaluations"] = evaluations[:100]
        context["reviewer_count"] = sum(evaluation.reviewers.count() for evaluation in evaluations)
        if period.evaluation_count:
            context["completion_percentage"] = round(period.completed_count / period.evaluation_count * 100, 1)
        else:
            context["completion_percentage"] = 0
        validation_key = f"period_validation_{period.pk}"
        context["validation"] = self.request.session.get(validation_key)
        score_count = EmployeePeriodScore.objects.filter(period=period).count()
        context["score_count"] = score_count
        context["score_missing_count"] = max(period.evaluation_count - score_count, 0)
        context["score_result"] = self.request.session.get(f"period_score_result_{period.pk}")
        context["all_evaluations_completed"] = (0 < period.evaluation_count == period.completed_count)
        context["all_scores_calculated"] = (0 < period.evaluation_count == score_count)

        return context
