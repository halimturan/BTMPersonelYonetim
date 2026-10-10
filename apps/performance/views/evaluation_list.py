from apps.performance.models import PerformanceEvaluation
from apps.performance.services.visibility import PerformanceEvaluationVisibilityService
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class EvaluationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PerformanceEvaluation
    template_name = "performance/evaluation_list.html"
    context_object_name = "evaluations"
    permission_required = "performance.view_performanceevaluation"
    paginate_by = 6

    def get_queryset(self):
        queryset = (
            PerformanceEvaluationVisibilityService(
                self.request.user
            )
            .get_visible_evaluations()
            .select_related(
                "employee",
                "employee__current_management_level",
                "period",
                "status",
                "template",
            )
            .prefetch_related(
                "reviewers",
                "reviewers__reviewer_employee",
                "reviewers__reviewer_employee__current_management_level",
                "reviewers__reviewer_role",
            )
        )

        # ==================================
        # Durum filtresi
        # ==================================

        status = self.request.GET.get("status", "").strip()

        if status == "pending":
            queryset = queryset.filter(completed_at__isnull=True)

        elif status == "completed":
            queryset = queryset.filter(completed_at__isnull=False)

        # status yoksa: Tümü

        return queryset.order_by("-period__start_date", "employee__first_name", "employee__last_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluation_rows = []

        for evaluation in context["evaluations"]:

            chief_review = None
            assistant_manager_review = None
            manager_review = None

            for review in evaluation.reviewers.all():
                reviewer_employee = review.reviewer_employee

                if not reviewer_employee:
                    continue

                level = reviewer_employee.current_management_level

                if not level:
                    continue

                if level.order == 20:
                    chief_review = review

                elif level.order == 30:
                    assistant_manager_review = review

                elif level.order == 40:
                    manager_review = review

            evaluation_rows.append({
                "evaluation": evaluation,
                "chief_review": chief_review,
                "assistant_manager_review": assistant_manager_review,
                "manager_review": manager_review,
            })

        context["evaluation_rows"] = evaluation_rows

        return context
