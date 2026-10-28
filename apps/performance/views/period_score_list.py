from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from apps.performance.models import EvaluationPeriod
from apps.employees.services.visibility import EmployeeVisibilityService
from apps.scoring.models import EmployeePeriodScore


class PeriodScoreListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EmployeePeriodScore
    template_name = "performance/period_score_list.html"
    context_object_name = "scores"
    permission_required = "scoring.view_employeeperiodscore"
    paginate_by = 7

    def dispatch(self, request, *args, **kwargs):
        self.period = get_object_or_404(EvaluationPeriod, pk=kwargs["period_pk"])
        return super().dispatch(request,*args, **kwargs)

    def get_queryset(self):

        visible_employee_ids = (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees()
            .values_list("pk", flat=True)
        )

        return (
            EmployeePeriodScore.objects
            .filter(period=self.period, employee_id__in=visible_employee_ids)
            .select_related("employee", "period", "formula")
            .prefetch_related("components", "components__component")
            .order_by("employee__first_name", "employee__last_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []

        for score in context["scores"]:

            components = {
                item.component.code: item for item in score.components.all()
            }

            rows.append({
                "score": score,
                "education": components.get("EDUCATION"),
                "job_role": components.get("JOB_ROLE"),
                "experience": components.get("EXPERIENCE"),
                "performance": components.get("PERFORMANCE"),
            })

        context.update({
            "period": self.period, "score_rows": rows
        })
        return context
