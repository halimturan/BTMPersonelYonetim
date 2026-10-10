from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from apps.performance.models import EvaluationPeriod
from apps.scoring.models import EmployeeUpgradeRecommendation


class PeriodUpgradeRecommendationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EmployeeUpgradeRecommendation
    template_name = "performance/period_upgrade_recommendation_list.html"
    context_object_name = "recommendations"
    permission_required = "scoring.view_employeeupgraderecommendation"
    paginate_by = 7

    def dispatch(self, request, *args, **kwargs):
        self.period = get_object_or_404(EvaluationPeriod, pk=kwargs["period_pk"])
        return super().dispatch(request,*args, **kwargs)

    def get_queryset(self):

        queryset = (
            EmployeeUpgradeRecommendation.objects
            .filter(period=self.period)
            .select_related(
                "employee",
                "period",
                "rule",
                "job_role",
                "current_level",
                "recommended_level",
            )
        )

        status = self.request.GET.get("status", "").strip()

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-recommendation_score", "employee__first_name", "employee__last_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_recommendations = EmployeeUpgradeRecommendation.objects.filter(period=self.period)

        context.update({
            "period": self.period,
            "total_count": all_recommendations.count(),
            "insufficient_count":
                all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.INSUFFICIENT_DATA).count(),
            "watch_count":
                all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.WATCH).count(),
            "candidate_count":
                all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.CANDIDATE).count(),
            "strong_count": all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.STRONG).count(),
        })

        return context
