from dataclasses import dataclass
from decimal import Decimal
from apps.employees.services.organization import EmployeeOrganizationService, ManagerNotFoundError, MultipleManagersFoundError


class ReviewerResolutionError(Exception):
    pass


@dataclass(frozen=True)
class ResolvedReviewer:
    employee: object
    reviewer_role: object
    management_level: object
    weight: object
    scheme_item: object


class ReviewerResolver:
    def __init__(self, reference_date):
        self.reference_date = reference_date
        self.organization_service = EmployeeOrganizationService(reference_date)

    def resolve(self, employee, reviewer_scheme):
        scheme_items = (
            reviewer_scheme.items
            .select_related("reviewer_role", "management_level")
            .order_by("order", "pk")
        )

        total_weight = sum((item.weight for item in scheme_items), Decimal("0"))

        if total_weight != Decimal("100"):
            raise ReviewerResolutionError(
                f"{reviewer_scheme.name} "
                f"değerlendirici ağırlıkları "
                f"100 olmalıdır. "
                f"Mevcut toplam: {total_weight}"
            )

        if not scheme_items.exists():
            raise ReviewerResolutionError(
                f"{reviewer_scheme.name} için "
                f"değerlendirici kuralı tanımlanmamış."
            )

        result = []
        used_employee_ids = set()

        for item in scheme_items:
            try:
                reviewer = (
                    self.organization_service.find_manager(employee=employee, target_management_level=item.management_level)
                )

            except (
                ManagerNotFoundError,
                MultipleManagersFoundError,
            ) as exc:
                raise ReviewerResolutionError(str(exc)) from exc

            if reviewer.pk == employee.pk:
                raise ReviewerResolutionError(f"{employee.full_name} kendi değerlendiricisi olamaz.")

            # Aynı kişi iki farklı reviewer rolüyle
            # atanmasın.
            if reviewer.pk in used_employee_ids:
                raise ReviewerResolutionError(
                    f"{reviewer.full_name}, "
                    f"{employee.full_name} için "
                    f"birden fazla değerlendirici "
                    f"rolüne çözülüyor."
                )

            used_employee_ids.add(reviewer.pk)

            result.append(
                ResolvedReviewer(
                    employee=reviewer,
                    reviewer_role=item.reviewer_role,
                    management_level=item.management_level,
                    weight=item.weight,
                    scheme_item=item,
                )
            )

        return result
