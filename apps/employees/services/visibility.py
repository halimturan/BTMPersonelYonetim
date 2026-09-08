from django.db.models import Q
from django.utils import timezone

from apps.employees.models import Employee, EmployeeTitleHistory
from apps.employees.services.organization import EmployeeOrganizationService


class EmployeeVisibilityService:
    def __init__(
        self,
        user,
        reference_date=None,
    ):
        self.user = user

        self.employee = getattr(
            user,
            "employee",
            None,
        )

        self.reference_date = (
            reference_date
            or timezone.localdate()
        )

        self.organization_service = (
            EmployeeOrganizationService(
                self.reference_date
            )
        )

    def get_visible_employees(
        self,
        include_self=False,
    ):
        # Sistem yöneticisi
        if self.user.is_superuser:
            return Employee.objects.filter(
                is_active=True
            )

        # User ile Employee bağlı değil
        if not self.employee:
            return Employee.objects.none()

        snapshot = (
            self.organization_service
            .get_snapshot(self.employee)
        )

        # Organizasyon kaydı yok
        if not snapshot.unit:
            if include_self:
                return Employee.objects.filter(
                    pk=self.employee.pk
                )

            return Employee.objects.none()

        # Yönetim seviyesi yok
        if not snapshot.management_level:
            if include_self:
                return Employee.objects.filter(
                    pk=self.employee.pk
                )

            return Employee.objects.none()

        # Normal personel
        if not snapshot.management_level.can_manage_people:
            if include_self:
                return Employee.objects.filter(
                    pk=self.employee.pk
                )

            return Employee.objects.none()

        # Yöneticinin kendi birimi + alt birimleri
        unit_ids = (
            self.organization_service
            .get_descendant_unit_ids(
                snapshot.unit,
                include_self=True,
            )
        )

        employee_ids = (
            self.organization_service
            .get_employee_ids_in_units(
                unit_ids
            )
        )

        queryset = Employee.objects.filter(
            pk__in=employee_ids,
            is_active=True,
        )

        # Kendinden düşük management level
        lower_level_employee_ids = (
            EmployeeTitleHistory.objects
            .filter(
                employee_id__in=employee_ids,

                start_date__lte=(
                    self.reference_date
                ),

                job_title__management_level__order__lt=(
                    snapshot
                    .management_level
                    .order
                ),
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=(
                        self.reference_date
                    )
                )
            )
            .values_list(
                "employee_id",
                flat=True,
            )
        )

        queryset = queryset.filter(
            pk__in=lower_level_employee_ids
        )

        if include_self:
            queryset = (
                Employee.objects
                .filter(
                    Q(pk__in=queryset.values("pk"))
                    | Q(pk=self.employee.pk)
                )
                .filter(is_active=True)
            )

        return queryset.distinct()

    def can_view(self, employee):
        if self.user.is_superuser:
            return True

        return (
            self.get_visible_employees(
                include_self=True
            )
            .filter(pk=employee.pk)
            .exists()
        )