from apps.employees.models import EmployeeLevelHistory
from django.db.models import Q
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from apps.performance.models import EvaluationPeriod
from apps.scoring.models import EmployeePeriodScore
from django.http import Http404
from apps.scoring.models import EmployeeUpgradeRecommendation
from apps.organization.models import CareerLevel


class PeriodUpgradeRecommendationDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = EmployeeUpgradeRecommendation
    template_name = "performance/period_upgrade_recommendation_detail.html"
    context_object_name = "recommendation"
    permission_required = "scoring.view_employeeupgraderecommendation"

    def dispatch(self, request, *args, **kwargs):
        self.period = get_object_or_404(
            EvaluationPeriod,
            pk=kwargs["period_pk"],
        )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):

        return (
            EmployeeUpgradeRecommendation.objects
            .select_related(
                "employee",
                "period",
                "rule",
                "job_role",
                "current_level",
                "recommended_level",
            )
        )

    def get_object(self, queryset=None):
        recommendation = super().get_object(queryset)

        if recommendation.period_id != self.kwargs["period_pk"]:
            raise Http404("Upgrade önerisi bulunamadı.")

        return recommendation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_recommendations = EmployeeUpgradeRecommendation.objects.filter(period=self.period)

        # ==========================================
        # Dönemde skoru hesaplanan personeller
        # ==========================================

        period_scores = EmployeePeriodScore.objects.filter(period=self.period).select_related("employee")
        scored_employee_ids = list(period_scores.values_list("employee_id", flat=True))
        recommendation_employee_ids = list(all_recommendations.values_list("employee_id", flat=True))
        skipped_employee_ids = set(scored_employee_ids) - set(recommendation_employee_ids)

        # ==========================================
        # En yüksek kariyer seviyesi
        # ==========================================

        max_level = CareerLevel.objects.filter(active=True).order_by("-order").first()
        max_level_employee_ids = set()

        if max_level:
            max_level_employee_ids = set(
                EmployeeLevelHistory.objects
                .filter(employee_id__in=skipped_employee_ids, level=max_level, start_date__lte=self.period.end_date)
                .filter(Q(end_date__isnull=True) | Q(end_date__gte=self.period.end_date))
                .values_list("employee_id", flat=True)
            )

        max_level_count = len(max_level_employee_ids)
        skipped_count = len(skipped_employee_ids)
        other_skipped_count = (skipped_count - max_level_count)

        recommendation = self.object
        explanation = recommendation.explanation or {}

        context.update({
            "period": self.period,

            # --------------------------------------
            # Analiz kapsamı
            # --------------------------------------
            "scored_count": len(scored_employee_ids),
            "analyzed_count": all_recommendations.count(),
            "skipped_count": skipped_count,
            "max_level_count": max_level_count,
            "other_skipped_count": other_skipped_count,
            "max_level": max_level,

            # --------------------------------------
            # Öneri durumları
            # --------------------------------------
            "total_count": all_recommendations.count(),
            "insufficient_count":
                all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.INSUFFICIENT_DATA).count(),
            "watch_count": all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.WATCH).count(),
            "candidate_count":all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.CANDIDATE).count(),
            "strong_count": all_recommendations.filter(status=EmployeeUpgradeRecommendation.Status.STRONG).count(),
            "employee": recommendation.employee,
            "explanation": explanation,
            "score_periods": explanation.get("periods", []),
            "peers": explanation.get("peers", []),
        })

        return context