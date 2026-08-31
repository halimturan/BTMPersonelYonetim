from django.db.models import Q
from django.utils import timezone
from apps.employees.models import (Employee, EmployeeReportingLine)


class EmployeeVisibilityService:

    def __init__(self, user):
        self.user = user
        self.employee = getattr(user, "employee", None)

    def get_visible_employees(self):
        """
        Kullanıcının görebileceği tüm personelleri döndürür.
        """

        if self.user.is_superuser:
            return Employee.objects.filter(is_active=True)

        if not self.employee:
            return Employee.objects.none()

        employee_ids = self._get_descendant_ids(self.employee.id)

        return (
            Employee.objects
            .filter(Q(id__in=employee_ids) | Q(id=self.employee.id))
            .filter(is_active=True)
            .distinct()
        )

    def _get_descendant_ids(self, manager_id):
        today = timezone.localdate()

        result = set()
        pending = [manager_id]

        while pending:
            current_manager_id = pending.pop()

            child_ids = list(
                EmployeeReportingLine.objects
                .filter(
                    manager_id=current_manager_id,
                    start_date__lte=today,
                )
                .filter(
                    Q(end_date__isnull=True)
                    | Q(end_date__gte=today)
                )
                .values_list(
                    "employee_id",
                    flat=True,
                )
            )

            for child_id in child_ids:
                if child_id not in result:
                    result.add(child_id)
                    pending.append(child_id)

        return result