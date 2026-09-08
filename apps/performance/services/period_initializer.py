from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.employees.models import Employee
from apps.performance.models import EvaluationProfile, EvaluationStatus, PerformanceEvaluation, PerformanceEvaluationReviewer
from apps.performance.services.reviewer_resolver import ReviewerResolutionError, ReviewerResolver
from apps.employees.services.organization import EmployeeOrganizationService


class PeriodInitializationError(Exception):
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

        title_record = (
            self.organization_service
            .get_title_record(employee)
        )

        department_record = (
            self.organization_service
            .get_department_record(employee)
        )

        job_title = (
            title_record.job_title
            if title_record
            else None
        )

        department = (
            department_record.department
            if department_record
            else None
        )

        queryset = (
            EvaluationProfile.objects
            .filter(active=True)
            .select_related(
                "reviewer_scheme",
                "reviewer_scheme__performance_template",
            )
            .order_by("-priority")
        )

        candidates = []

        for profile in queryset:
            if (
                profile.employment_type_id
                and profile.employment_type_id
                != employee.employment_type_id
            ):
                continue

            if (
                profile.job_title_id
                and (
                    not job_title
                    or profile.job_title_id
                    != job_title.pk
                )
            ):
                continue

            if (
                profile.department_id
                and (
                    not department
                    or profile.department_id
                    != department.pk
                )
            ):
                continue

            candidates.append(profile)

        if not candidates:
            raise PeriodInitializationError(
                f"{employee} için değerlendirme profili bulunamadı."
            )

        highest_priority = candidates[0].priority

        same_priority = [
            profile
            for profile in candidates
            if profile.priority == highest_priority
        ]

        if len(same_priority) > 1:
            raise PeriodInitializationError(
                f"{employee} için aynı öncelikte "
                f"birden fazla değerlendirme profili bulundu."
            )

        return candidates[0]


class EvaluationPeriodInitializer:
    def __init__(self, period):
        self.period = period

        # Organizasyon yapısını hangi tarihe göre
        # donduracağımızı burada belirliyoruz.
        self.reference_date = period.end_date

        self.profile_resolver = (
            EvaluationProfileResolver(self.reference_date)
        )

        self.reviewer_resolver = ReviewerResolver(
            self.reference_date
        )

    @transaction.atomic
    def initialize(self):
        if self.period.is_locked:
            raise PeriodInitializationError(
                "Kilitli dönem başlatılamaz."
            )

        status = EvaluationStatus.objects.get(
            code="PENDING"
        )

        employees = (
            Employee.objects
            .filter(is_active=True)
            .select_related("employment_type")
        )

        created_count = 0

        for employee in employees:
            profile = self.profile_resolver.resolve(
                employee
            )

            reviewer_scheme = profile.reviewer_scheme

            template = (
                reviewer_scheme.performance_template
            )

            reviewers = self.reviewer_resolver.resolve(
                employee=employee,
                reviewer_scheme=reviewer_scheme,
            )

            evaluation, created = (
                PerformanceEvaluation.objects
                .get_or_create(
                    employee=employee,
                    period=self.period,
                    defaults={
                        "template": template,
                        "reviewer_scheme": reviewer_scheme,
                        "status": status,
                    },
                )
            )

            if not created:
                continue

            for resolved in reviewers:
                PerformanceEvaluationReviewer.objects.create(
                    evaluation=evaluation,
                    reviewer_employee=resolved.employee,
                    reviewer_role=(
                        resolved.scheme_item.reviewer_role
                    ),
                    weight=resolved.scheme_item.weight,
                )

            created_count += 1

        return created_count