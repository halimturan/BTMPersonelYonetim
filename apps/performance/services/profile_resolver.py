from apps.performance.models import EvaluationProfile

from apps.employees.services.organization import EmployeeOrganizationService


class EvaluationProfileResolutionError(Exception):
    pass


class EvaluationProfileResolver:
    def __init__(self, reference_date):
        self.reference_date = reference_date

        self.organization_service = (
            EmployeeOrganizationService(
                reference_date
            )
        )

    def resolve(self, employee):
        snapshot = (
            self.organization_service
            .get_snapshot(employee)
        )

        candidates = (
            EvaluationProfile.objects
            .filter(active=True)
            .select_related(
                "reviewer_scheme",
                "management_level",
                "job_title",
                "employment_type",
                "department",
            )
            .order_by(
                "-priority",
                "pk",
            )
        )

        matched = []

        for profile in candidates:
            if (
                profile.management_level_id
                and profile.management_level_id
                != getattr(
                    snapshot.management_level,
                    "pk",
                    None,
                )
            ):
                continue

            if (
                profile.job_title_id
                and profile.job_title_id
                != getattr(
                    snapshot.job_title,
                    "pk",
                    None,
                )
            ):
                continue

            if (
                profile.employment_type_id
                and profile.employment_type_id
                != employee.employment_type_id
            ):
                continue

            if (
                profile.department_id
                and profile.department_id
                != getattr(
                    snapshot.department,
                    "pk",
                    None,
                )
            ):
                continue

            matched.append(profile)

        if not matched:
            raise EvaluationProfileResolutionError(
                f"{employee.full_name} için "
                f"uygun değerlendirme profili bulunamadı."
            )

        highest_priority = (
            matched[0].priority
        )

        same_priority = [
            profile
            for profile in matched
            if profile.priority
            == highest_priority
        ]

        if len(same_priority) > 1:
            names = ", ".join(
                profile.name
                for profile in same_priority
            )

            raise EvaluationProfileResolutionError(
                f"{employee.full_name} için "
                f"aynı öncelikte birden fazla "
                f"değerlendirme profili bulundu: "
                f"{names}"
            )

        return matched[0]