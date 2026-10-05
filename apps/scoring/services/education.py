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
        # ----------------------------------
        # Puanlamada kullanılacak eğitim
        # ----------------------------------

        education = self.employee.educations.filter(is_primary_for_scoring=True).select_related("education_level").first()

        if not education:
            raise EducationScoreCalculationError("Puanlamada kullanılacak eğitim kaydı bulunamadı.")

        if not education.education_level_id:
            raise EducationScoreCalculationError("Puanlamada kullanılacak eğitim seviyesi tanımlanmamış.")

        # ----------------------------------
        # Geçerli eğitim puanı
        # ----------------------------------

        rules = (
            EducationScoreRule.objects
            .filter(education_level_id=education.education_level_id, active=True, valid_from__lte=self.reference_date)
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=self.reference_date))
            .order_by("-valid_from", "-pk")
        )

        # ----------------------------------
        # Kural kontrolü
        # ----------------------------------

        if not rules.exists():
            raise EducationScoreCalculationError(
                (
                    f"{education.education_level} eğitim seviyesi için "
                    f"{self.reference_date} tarihinde geçerli puanlama kuralı bulunamadı."
                )
            )

        if rules.count() > 1:
            raise EducationScoreCalculationError(
                (
                    f"{education.education_level} eğitim seviyesi için aynı tarihte "
                    "birden fazla geçerli puanlama kuralı bulundu."
                )
            )

        rule = rules.first()

        return Decimal(str(rule.score))
