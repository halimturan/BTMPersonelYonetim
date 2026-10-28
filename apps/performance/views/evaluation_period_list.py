from django.db.models import Count, Q
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.performance.models import EvaluationPeriod


class EvaluationPeriodListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EvaluationPeriod
    template_name = "performance/period_list.html"
    context_object_name = "periods"
    permission_required = "performance.view_evaluationperiod"

    paginate_by = 20

    def get_queryset(self):
        return (
            EvaluationPeriod.objects
            .annotate(
                evaluation_count=Count("evaluations", distinct=True),
                completed_count=Count("evaluations", filter=Q(evaluations__completed_at__isnull=False), distinct=True),
            )
            .order_by("-start_date")
        )
