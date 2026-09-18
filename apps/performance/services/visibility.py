from apps.performance.models import PerformanceEvaluation
from apps.employees.services.visibility import EmployeeVisibilityService


class PerformanceEvaluationVisibilityService:

    def __init__(self, user):
        self.user = user

    def get_visible_evaluations(self):

        employee_ids = (
            EmployeeVisibilityService(
                self.user
            )
            .get_visible_employees()
            .values_list(
                "id",
                flat=True,
            )
        )

        return (
            PerformanceEvaluation.objects
            .filter(
                employee_id__in=employee_ids
            )
            .select_related(
                "employee",
                "period",
                "status",
                "template",
            )
        )

    def can_view(self, evaluation):
        return (
            self.get_visible_evaluations()
            .filter(
                pk=evaluation.pk
            )
            .exists()
        )