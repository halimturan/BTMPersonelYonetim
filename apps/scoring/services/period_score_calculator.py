from dataclasses import dataclass, field

from apps.scoring.services.final_score import (
    EmployeeFinalScoreCalculator,
    FinalScoreCalculationError,
)


@dataclass
class PeriodScoreIssue:
    employee_id: int
    employee_name: str
    personnel_no: str
    message: str


@dataclass
class PeriodScoreResult:
    employee_count: int = 0
    success_count: int = 0
    issues: list = field(default_factory=list)

    @property
    def error_count(self):
        return len(self.issues)

    @property
    def valid(self):
        return self.error_count == 0


class PeriodScoreCalculator:
    def __init__(self, period):
        self.period = period

    def calculate(self):
        result = PeriodScoreResult()

        evaluations = (
            self.period.evaluations
            .select_related("employee")
            .order_by(
                "employee__first_name",
                "employee__last_name",
            )
        )

        result.employee_count = (
            evaluations.count()
        )

        for evaluation in evaluations:
            employee = evaluation.employee

            if evaluation.completed_at is None:
                result.issues.append(
                    PeriodScoreIssue(
                        employee_id=employee.pk,
                        employee_name=employee.full_name,
                        personnel_no=employee.personnel_no,
                        message=(
                            "Performans değerlendirmesi "
                            "henüz tamamlanmadı."
                        ),
                    )
                )
                continue

            try:
                (
                    EmployeeFinalScoreCalculator(
                        employee=employee,
                        period=self.period,
                    )
                    .calculate_and_save()
                )

                result.success_count += 1

            except FinalScoreCalculationError as exc:
                result.issues.append(
                    PeriodScoreIssue(
                        employee_id=employee.pk,
                        employee_name=employee.full_name,
                        personnel_no=employee.personnel_no,
                        message=str(exc),
                    )
                )

            except Exception as exc:
                result.issues.append(
                    PeriodScoreIssue(
                        employee_id=employee.pk,
                        employee_name=employee.full_name,
                        personnel_no=employee.personnel_no,
                        message=(
                            "Skor hesaplanırken beklenmeyen "
                            f"bir hata oluştu: {exc}"
                        ),
                    )
                )

        return result