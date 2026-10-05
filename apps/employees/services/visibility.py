from django.utils import timezone
from apps.employees.models import Employee
from apps.employees.services.organization import EmployeeOrganizationService
from apps.organization.models import ManagementLevel


class EmployeeVisibilityService:
    def __init__(self, user, reference_date=None):
        self.user = user
        self.reference_date = reference_date or timezone.localdate()

        self.organization_service = EmployeeOrganizationService(reference_date=self.reference_date)

    def get_visible_employees(self):
        if self.user.is_superuser:
            return Employee.objects.filter(is_active=True)

        employee = getattr(
            self.user,
            "employee",
            None,
        )

        if not employee:
            return Employee.objects.none()

        snapshot = self.organization_service.get_snapshot(employee)

        management_level = snapshot.management_level

        if not management_level:
            return Employee.objects.none()

        if not management_level.can_manage_people:
            return Employee.objects.none()

        scope = management_level.visibility_scope

        if scope == ManagementLevel.VisibilityScope.OWN_UNIT:
            return self._employees_in_same_unit(
                employee,
                snapshot,
            )

        if scope == ManagementLevel.VisibilityScope.UNIT_TREE:
            return self._employees_in_same_department(
                employee,
                snapshot,
            )

        if scope == ManagementLevel.VisibilityScope.ALL:
            return(
                Employee.objects
                .filter(is_active=True, current_management_level__order__lt=management_level.order)
                .exclude(pk=employee.pk)
                .distinct()
            )

        return Employee.objects.none()

    def _employees_in_same_unit(self, employee, snapshot):
        if not snapshot.unit:
            return Employee.objects.none()

        employee_ids = self.organization_service.get_employee_ids_in_unit(snapshot.unit)

        return (
            Employee.objects
            .filter(
                pk__in=employee_ids,
                is_active=True,
                current_management_level__order__lt=snapshot.management_level.order,
            )
            .exclude(pk=employee.pk)
            .select_related("employment_type", "current_management_level")
            .distinct()
        )

    def _employees_in_same_department(self, employee, snapshot):
        if not snapshot.department:
            return Employee.objects.none()

        employee_ids = self.organization_service.get_employee_ids_in_department(snapshot.department)

        return (
            Employee.objects
            .filter(
                pk__in=employee_ids,
                is_active=True,
                current_management_level__order__lt=snapshot.management_level.order,
            )
            .exclude(pk=employee.pk)
            .select_related("employment_type", "current_management_level")
            .distinct()
        )

    def can_view(self, employee):
        # Superuser her personeli görebilir
        if self.user.is_superuser:
            return True

        current_employee = getattr(self.user, "employee", None)

        if not current_employee:
            return False

        # Kullanıcı her zaman kendi profilini görebilir
        if current_employee.pk == employee.pk:
            return True

        # Diğer personeller için normal
        # organizasyon görünürlük kuralları geçerli
        return self.get_visible_employees().filter(pk=employee.pk).exists()