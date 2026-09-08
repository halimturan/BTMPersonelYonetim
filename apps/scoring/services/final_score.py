from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from apps.employees.services.organization import EmployeeOrganizationService
from apps.scoring.models import EmployeePeriodScore, EmployeePeriodScoreComponent, ScoreFormula

from apps.scoring.services.education import EducationScoreCalculator
from apps.scoring.services.experience import ExperienceScoreCalculator
from apps.scoring.services.job_role import JobRoleScoreCalculator
from apps.scoring.services.performance import PerformanceScoreCalculator


class FinalScoreCalculationError(Exception):
    pass


@dataclass
class CalculatedComponent:
    code: str
    name: str
    raw_score: Decimal
    weight: Decimal
    weighted_score: Decimal


@dataclass
class FinalScoreResult:
    final_score: Decimal
    components: list


class EmployeeFinalScoreCalculator:
    def __init__(
        self,
        employee,
        period,
    ):
        self.employee = employee
        self.period = period
        self.reference_date = period.end_date

    def _resolve_formula(self):
        formulas = (
            ScoreFormula.objects
            .filter(
                active=True,
                valid_from__lte=self.reference_date,
            )
            .filter(
                Q(valid_to__isnull=True) | Q(valid_to__gte=self.reference_date)
            )
        )

        if not formulas.exists():
            raise FinalScoreCalculationError(
                "Geçerli nihai skor formülü bulunamadı."
            )

        if formulas.count() > 1:
            raise FinalScoreCalculationError(
                "Birden fazla aktif nihai skor formülü bulundu."
            )

        return formulas.first()

    def _raw_score_for_component(
        self,
        code,
        job_role,
    ):
        if code == "EDUCATION":
            return (
                EducationScoreCalculator(
                    self.employee,
                    self.reference_date,
                )
                .calculate()
            )

        if code == "JOB_ROLE":
            return (
                JobRoleScoreCalculator(
                    job_role,
                    self.reference_date,
                )
                .calculate()
            )

        if code == "EXPERIENCE":
            return (
                ExperienceScoreCalculator(
                    self.employee,
                    self.reference_date,
                )
                .calculate()
            )

        if code == "PERFORMANCE":
            return (
                PerformanceScoreCalculator(
                    self.employee,
                    self.period,
                )
                .calculate()
            )

        raise FinalScoreCalculationError(
            f"Desteklenmeyen skor bileşeni: {code}"
        )

    def calculate(self):
        formula = self._resolve_formula()

        formula_components = (
            formula.components
            .select_related("component")
            .order_by("order")
        )

        if not formula_components.exists():
            raise FinalScoreCalculationError(
                "Skor formülünde bileşen bulunmuyor."
            )

        total_weight = sum(
            (
                item.weight
                for item in formula_components
            ),
            Decimal("0"),
        )

        if total_weight != Decimal("100"):
            raise FinalScoreCalculationError(
                (
                    "Nihai skor formülü ağırlıkları "
                    f"100 değil: {total_weight}"
                )
            )

        organization_service = (
            EmployeeOrganizationService(
                self.reference_date
            )
        )

        job_role = (
            organization_service
            .get_job_role(
                self.employee
            )
        )

        calculated_components = []

        final_score = Decimal("0")

        for item in formula_components:
            component = item.component

            raw_score = (
                self._raw_score_for_component(
                    component.code,
                    job_role,
                )
            )

            weighted_score = (
                raw_score
                * item.weight
                / Decimal("100")
            ).quantize(
                Decimal("0.0001")
            )

            final_score += weighted_score

            calculated_components.append(
                CalculatedComponent(
                    code=component.code,
                    name=component.name,
                    raw_score=raw_score,
                    weight=item.weight,
                    weighted_score=weighted_score,
                )
            )

        return FinalScoreResult(
            final_score=final_score.quantize(
                Decimal("0.0001")
            ),
            components=calculated_components,
        )

    @transaction.atomic
    def calculate_and_save(self):
        result = self.calculate()

        formula = self._resolve_formula()

        period_score, _ = (
            EmployeePeriodScore.objects
            .update_or_create(
                employee=self.employee,
                period=self.period,
                defaults={
                    "formula": formula,
                    "final_score":
                        result.final_score,
                },
            )
        )

        period_score.components.all().delete()

        for item in result.components:
            formula_component = (
                formula.components
                .select_related("component")
                .get(
                    component__code=item.code
                )
            )

            EmployeePeriodScoreComponent.objects.create(
                period_score=period_score,
                component=formula_component.component,
                raw_score=item.raw_score,
                weight=item.weight,
                weighted_score=item.weighted_score,
                source_data={
                    "period_id": self.period.pk,
                    "reference_date":
                        str(self.reference_date),
                },
            )

        return period_score