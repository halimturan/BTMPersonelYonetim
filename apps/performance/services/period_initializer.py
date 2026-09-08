from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction

from apps.employees.models import Employee
from apps.performance.models import (
    EvaluationStatus,
    PerformanceEvaluation,
    PerformanceEvaluationReviewer,
)
from apps.performance.services.profile_resolver import (
    EvaluationProfileResolutionError,
    EvaluationProfileResolver,
)
from apps.performance.services.reviewer_resolver import (
    ReviewerResolutionError,
    ReviewerResolver,
)


class PeriodInitializationError(Exception):
    pass


@dataclass
class PeriodValidationIssue:
    employee_id: int | None
    personnel_no: str
    employee_name: str
    message: str
    severity: str = "error"


@dataclass
class PeriodValidationResult:
    valid: bool = True
    issues: list = field(default_factory=list)
    employee_count: int = 0
    ready_count: int = 0

    @property
    def error_count(self):
        return len(
            [
                issue
                for issue in self.issues
                if issue.severity == "error"
            ]
        )

    @property
    def warning_count(self):
        return len(
            [
                issue
                for issue in self.issues
                if issue.severity == "warning"
            ]
        )

    def add_error(
        self,
        message,
        employee=None,
    ):
        self.valid = False

        self.issues.append(
            PeriodValidationIssue(
                employee_id=(
                    employee.pk
                    if employee
                    else None
                ),
                personnel_no=(
                    employee.personnel_no
                    if employee
                    else "-"
                ),
                employee_name=(
                    employee.full_name
                    if employee
                    else "Sistem"
                ),
                message=message,
                severity="error",
            )
        )

    def add_warning(
        self,
        message,
        employee=None,
    ):
        self.issues.append(
            PeriodValidationIssue(
                employee_id=(
                    employee.pk
                    if employee
                    else None
                ),
                personnel_no=(
                    employee.personnel_no
                    if employee
                    else "-"
                ),
                employee_name=(
                    employee.full_name
                    if employee
                    else "Sistem"
                ),
                message=message,
                severity="warning",
            )
        )


class EvaluationPeriodInitializer:
    def __init__(self, period):
        self.period = period
        self.reference_date = period.end_date

    def _employees(self):
        return (
            Employee.objects
            .filter(is_active=True)
            .select_related("employment_type")
            .order_by(
                "first_name",
                "last_name",
            )
        )

    def validate(self):
        result = PeriodValidationResult()

        employees = self._employees()

        result.employee_count = employees.count()

        if self.period.is_locked:
            result.add_error(
                "Kilitli bir dönem başlatılamaz."
            )

            return result

        profile_resolver = (
            EvaluationProfileResolver(
                self.reference_date
            )
        )

        reviewer_resolver = (
            ReviewerResolver(
                self.reference_date
            )
        )

        for employee in employees:
            try:
                profile = (
                    profile_resolver.resolve(
                        employee
                    )
                )

            except EvaluationProfileResolutionError as exc:
                result.add_error(
                    str(exc),
                    employee,
                )
                continue

            scheme = profile.reviewer_scheme

            if not scheme.active:
                result.add_error(
                    (
                        f"{scheme.name} değerlendirici "
                        f"şeması aktif değil."
                    ),
                    employee,
                )
                continue

            if (
                scheme.valid_from
                and scheme.valid_from
                > self.reference_date
            ):
                result.add_error(
                    (
                        f"{scheme.name} değerlendirici "
                        f"şeması dönem tarihinde "
                        f"henüz geçerli değil."
                    ),
                    employee,
                )
                continue

            if (
                scheme.valid_to
                and scheme.valid_to
                < self.reference_date
            ):
                result.add_error(
                    (
                        f"{scheme.name} değerlendirici "
                        f"şemasının geçerliliği sona ermiş."
                    ),
                    employee,
                )
                continue

            template = scheme.performance_template

            if not template.active:
                result.add_error(
                    (
                        f"{template.name} performans "
                        f"şablonu aktif değil."
                    ),
                    employee,
                )
                continue

            try:
                template_items = list(
                    template.criteria.all()
                )

            except Exception:
                result.add_error(
                    (
                        f"{template.name} performans "
                        f"şablonunun kriterleri okunamadı."
                    ),
                    employee,
                )
                continue

            if not template_items:
                result.add_error(
                    (
                        f"{template.name} performans "
                        f"şablonunda kriter bulunmuyor."
                    ),
                    employee,
                )
                continue

            criterion_total = sum(
                (
                    item.max_score
                    for item in template_items
                ),
                Decimal("0"),
            )

            if criterion_total != Decimal("100"):
                result.add_error(
                    (
                        f"{template.name} kriter puanları "
                        f"toplamı 100 değil. "
                        f"Mevcut toplam: {criterion_total}"
                    ),
                    employee,
                )
                continue

            try:
                reviewers = reviewer_resolver.resolve(
                    employee=employee,
                    reviewer_scheme=scheme,
                )

            except ReviewerResolutionError as exc:
                result.add_error(
                    str(exc),
                    employee,
                )
                continue

            if not reviewers:
                result.add_error(
                    "Değerlendirici bulunamadı.",
                    employee,
                )
                continue

            result.ready_count += 1

        return result

    @transaction.atomic
    def initialize(self):
        validation = self.validate()

        if not validation.valid:
            raise PeriodInitializationError(
                (
                    "Dönem başlatılamadı. "
                    f"{validation.error_count} hata bulundu."
                )
            )

        if self.period.is_locked:
            raise PeriodInitializationError(
                "Kilitli dönem başlatılamaz."
            )

        status = (
            EvaluationStatus.objects
            .filter(
                code="PENDING",
                active=True,
            )
            .first()
        )

        if not status:
            raise PeriodInitializationError(
                (
                    "PENDING değerlendirme durumu "
                    "tanımlanmamış."
                )
            )

        profile_resolver = (
            EvaluationProfileResolver(
                self.reference_date
            )
        )

        reviewer_resolver = (
            ReviewerResolver(
                self.reference_date
            )
        )

        created_count = 0
        existing_count = 0

        for employee in self._employees():
            profile = profile_resolver.resolve(
                employee
            )

            scheme = profile.reviewer_scheme
            template = scheme.performance_template

            reviewers = reviewer_resolver.resolve(
                employee=employee,
                reviewer_scheme=scheme,
            )

            evaluation, created = (
                PerformanceEvaluation.objects
                .get_or_create(
                    employee=employee,
                    period=self.period,
                    defaults={
                        "template": template,
                        "reviewer_scheme": scheme,
                        "status": status,
                    },
                )
            )

            if not created:
                existing_count += 1
                continue

            for resolved in reviewers:
                (
                    PerformanceEvaluationReviewer.objects
                    .create(
                        evaluation=evaluation,
                        reviewer_employee=(
                            resolved.employee
                        ),
                        reviewer_role=(
                            resolved.reviewer_role
                        ),
                        weight=resolved.weight,
                    )
                )

            created_count += 1

        self.period.is_active = True

        self.period.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        return {
            "created_count": created_count,
            "existing_count": existing_count,
        }