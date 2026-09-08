from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.employees.services.visibility import EmployeeVisibilityService
from apps.performance.models import PerformanceEvaluationReviewer


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        employee = getattr(
            user,
            "employee",
            None,
        )

        visibility_service = (
            EmployeeVisibilityService(user)
        )

        visible_employees = (
            visibility_service
            .get_visible_employees()
        )

        pending_reviews = (
            PerformanceEvaluationReviewer.objects.none()
        )

        if employee:
            pending_reviews = (
                PerformanceEvaluationReviewer.objects
                .filter(reviewer_employee=employee, submitted_at__isnull=True)
                .select_related("evaluation", "evaluation__employee", "evaluation__period")
            )

        context.update({
            "visible_employee_count": visible_employees.count(),
            "pending_review_count": pending_reviews.count(),
            "pending_reviews": pending_reviews[:5],
        })

        return context