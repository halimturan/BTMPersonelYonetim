from apps.performance.models import PerformanceEvaluationReviewer
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin


class MyReviewListView(LoginRequiredMixin, ListView):
    template_name = "performance/my_review_list.html"
    context_object_name = "reviews"
    paginate_by = 6

    def get_queryset(self):
        employee = getattr(self.request.user, "employee", None)

        if not employee:
            return PerformanceEvaluationReviewer.objects.none()

        queryset = (
            PerformanceEvaluationReviewer.objects
            .filter(reviewer_employee=employee)
            .select_related("evaluation", "evaluation__employee", "evaluation__period", "reviewer_role")
            .order_by("submitted_at", "-evaluation__period__start_date")
        )

        status = self.request.GET.get("status")

        if status == "pending":
            queryset = queryset.filter(submitted_at__isnull=True)

        elif status == "completed":
            queryset = queryset.filter(submitted_at__isnull=False)

        return queryset
