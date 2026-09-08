from decimal import Decimal
from django.db.models import Q
from apps.scoring.models import EducationScoreRule


class EducationScoreCalculationError(Exception):
    pass


class EducationScoreCalculator:
    def __init__(self, employee, reference_date):
        self.employee = employee
        self.reference_date = reference_date

    def calculate(self):
        education = (
            self.employee.educations
            .filter(is_primary_for_scoring=True)
            .select_related("education_level")
            .first()
        )

        if not education:
            raise EducationScoreCalculationError(
                "Puanlamada kullanılacak eğitim kaydı bulunamadı."
            )

        rules = (
            EducationScoreRule.objects
            .filter(
                active=True,
                valid_from__lte=self.reference_date,
            )
            .filter(
                Q(valid_to__isnull=True)
                | Q(valid_to__gte=self.reference_date)
            )
            .order_by("-priority", "pk")
        )

        matched_rules = []

        for rule in rules:
            if (
                rule.education_level_id
                and rule.education_level_id
                != education.education_level_id
            ):
                continue

            if (
                rule.is_it_related is not None
                and rule.is_it_related
                != education.is_it_related
            ):
                continue

            if (
                rule.is_engineering is not None
                and rule.is_engineering
                != education.is_engineering
            ):
                continue

            if (
                rule.is_open_education is not None
                and rule.is_open_education
                != education.is_open_education
            ):
                continue

            matched_rules.append(rule)

        if not matched_rules:
            raise EducationScoreCalculationError(
                "Eğitim bilgisine uygun puanlama kuralı bulunamadı."
            )

        highest_priority = matched_rules[0].priority

        same_priority = [
            rule
            for rule in matched_rules
            if rule.priority == highest_priority
        ]

        if len(same_priority) > 1:
            raise EducationScoreCalculationError(
                "Eğitim puanı için birden fazla eşit öncelikli kural bulundu."
            )

        return Decimal(
            str(matched_rules[0].score)
        )