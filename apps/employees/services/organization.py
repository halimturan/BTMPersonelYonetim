from dataclasses import dataclass
from datetime import date

from django.db.models import Q
from django.db import models

from apps.employees.models import Employee, EmployeeDepartmentHistory, EmployeeTitleHistory
from apps.organization.models import ManagementLevel, Unit


class OrganizationResolutionError(Exception):
    pass


class MultipleManagersFoundError(OrganizationResolutionError):
    pass


class ManagerNotFoundError(OrganizationResolutionError):
    pass


@dataclass
class EmployeeOrganizationSnapshot:
    employee: Employee
    unit: Unit | None
    department: object | None
    job_title: object | None
    management_level: ManagementLevel | None


class EmployeeOrganizationService:
    def __init__(self, reference_date: date):
        self.reference_date = reference_date

    # ----------------------------------------
    # Aktif kayıtlar
    # ----------------------------------------

    def get_department_record(self, employee):
        return (
            EmployeeDepartmentHistory.objects
            .filter(employee=employee, start_date__lte=self.reference_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=self.reference_date))
            .select_related("department", "unit",)
            .order_by("-start_date")
            .first()
        )

    def get_title_record(self, employee):
        return (
            EmployeeTitleHistory.objects
            .filter(employee=employee, start_date__lte=self.reference_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=self.reference_date))
            .select_related("job_title")
            .order_by("-start_date")
            .first()
        )

    def get_management_level_record(self, employee):
        return (
            employee.management_level_history
            .filter(start_date__lte=self.reference_date,)
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=self.reference_date))
            .select_related("management_level")
            .order_by("-start_date", "-pk")
            .first()
        )

    def get_management_level(self, employee):
        record = self.get_management_level_record(employee)

        if record:
            return record.management_level

        return employee.current_management_level

    def get_assignment_record(self, employee):
        return (
            employee.assignments
            .filter(
                start_date__lte=self.reference_date,
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(end_date__gte=self.reference_date)
            )
            .select_related("job_role")
            .order_by("-start_date")
            .first()
        )

    def get_job_role(self, employee):
        record = self.get_assignment_record(employee)

        return (
            record.job_role
            if record
            else None
        )

    # ----------------------------------------
    # Snapshot
    # ----------------------------------------

    def get_snapshot(self, employee):

        department_record = self.get_department_record(employee)
        title_record = self.get_title_record(employee)
        management_level = self.get_management_level(employee)

        return EmployeeOrganizationSnapshot(
            employee=employee,
            unit=department_record.unit if department_record else None,
            department=department_record.department if department_record else None,
            job_title=(title_record.job_title if title_record else None),
            management_level = management_level
        )

    # ----------------------------------------
    # Unit ağacı
    # ----------------------------------------

    def get_ancestor_units(self, unit, include_self=True):
        result = []

        current = unit if include_self else unit.parent
        visited = set()

        while current:
            if current.pk in visited:
                raise OrganizationResolutionError("Organizasyon ağacında döngü tespit edildi.")

            visited.add(current.pk)
            result.append(current)

            current = current.parent

        return result

    def get_descendant_unit_ids(self, unit, include_self=True):
        result = {unit.pk} if include_self else set()
        pending = [unit.pk]

        while pending:
            parent_id = pending.pop()

            child_ids = list(
                Unit.objects
                .filter(parent_id=parent_id, active=True)
                .values_list("pk", flat=True)
            )

            for child_id in child_ids:
                if child_id not in result:
                    result.add(child_id)
                    pending.append(child_id)

        return result

    # ----------------------------------------
    # Birimdeki çalışanlar
    # ----------------------------------------

    def get_employee_ids_in_units(self, unit_ids):
        return (
            EmployeeDepartmentHistory.objects
            .filter(unit_id__in=unit_ids, start_date__lte=self.reference_date)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=self.reference_date))
            .values_list("employee_id", flat=True)
            .distinct()
        )

    def get_employee_ids_in_unit(self, unit):
        return (
            EmployeeDepartmentHistory.objects
            .filter(unit=unit, start_date__lte=self.reference_date)
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=self.reference_date))
            .values_list("employee_id", flat=True)
            .distinct()
        )

    def get_employees_in_unit(self, unit):
        employee_ids = self.get_employee_ids_in_units([unit.pk])
        return Employee.objects.filter(pk__in=employee_ids, is_active=True)

    def get_employee_ids_in_department(self, department):
        return (
            EmployeeDepartmentHistory.objects
            .filter(department=department, start_date__lte=self.reference_date)
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=self.reference_date))
            .values_list("employee_id", flat=True)
            .distinct()
        )

    # ----------------------------------------
    # ManagementLevel'a göre personel bulma
    # ----------------------------------------

    def get_employees_in_unit_by_level(self, unit, management_level):
        employee_ids = self.get_employee_ids_in_units([unit.pk])

        return (
            Employee.objects
            .filter(pk__in=employee_ids, is_active=True)
            .filter(title_history__start_date__lte=self.reference_date,)
            .filter(Q(title_history__end_date__isnull=True) | Q(title_history__end_date__gte=self.reference_date))
            .distinct()
        )

    # ----------------------------------------
    # Yönetici çözümleme
    # ----------------------------------------

    def find_manager(self, employee, target_management_level):
        current_employee = employee
        visited_employee_ids = set()

        while True:
            if current_employee.pk in visited_employee_ids:
                raise ManagerNotFoundError(
                    f"{employee.full_name} için yönetici zincirinde döngü tespit edildi."
                )

            visited_employee_ids.add(current_employee.pk)

            current_snapshot = self.get_snapshot(current_employee)

            current_level = current_snapshot.management_level

            if not current_level:
                raise ManagerNotFoundError(
                    f"{current_employee.full_name} için "
                    f"yönetim seviyesi bulunamadı."
                )

            parent_level = current_level.parent_level

            if not parent_level:
                raise ManagerNotFoundError(
                    f"{employee.full_name} için "
                    f"{target_management_level.name} seviyesine "
                    f"ulaşılamadı."
                )

            direct_manager = self._find_direct_manager(current_employee, current_snapshot, parent_level)

            if direct_manager.current_management_level_id == target_management_level.pk:
                return direct_manager

            current_employee = direct_manager

    def _find_direct_manager(self, employee, snapshot, parent_level):
        qs = (
            Employee.objects
            .filter(is_active=True, current_management_level=parent_level)
            .exclude(pk=employee.pk)
        )

        # Personel -> Şef
        if snapshot.unit:
            employee_ids = self.get_employee_ids_in_unit(snapshot.unit)

            same_unit_qs = qs.filter(pk__in=employee_ids)

            if same_unit_qs.exists():
                return self._get_single_manager(same_unit_qs, employee, parent_level)

        # Şef -> Müdür Yardımcısı
        if snapshot.department:
            employee_ids = self.get_employee_ids_in_department(snapshot.department)

            same_department_qs = qs.filter(pk__in=employee_ids)

            if same_department_qs.exists():
                return self._get_single_manager(same_department_qs, employee, parent_level)

        # Müdür Yardımcısı -> Müdür
        return self._get_single_manager(qs, employee, parent_level)

    def _get_single_manager(self, queryset, employee, management_level):
        count = queryset.count()

        if count == 0:
            raise ManagerNotFoundError(
                f"{employee.full_name} için {management_level.name} bulunamadı."
            )

        if count > 1:
            raise MultipleManagersFoundError(
                f"{employee.full_name} için birden fazla {management_level.name} bulundu."
            )

        return queryset.first()
