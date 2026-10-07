from apps.scoring.models import EmployeePeriodScore, UpgradeRecommendationRule
from apps.scoring.services.upgrade_recommendation import UpgradeRecommendationService, UpgradeRecommendationError


class PeriodUpgradeRecommendationService:
    """
    Bir değerlendirme dönemi için nihai skoru
    hesaplanmış tüm personellerin upgrade
    önerilerini üretir.
    """

    def __init__(self, period, rule=None):
        self.period = period
        self.rule = rule or UpgradeRecommendationRule.objects.filter(active=True).order_by("-pk").first()

        if not self.rule:
            raise UpgradeRecommendationError("Aktif upgrade öneri kuralı bulunamadı.")

    # =========================================================
    # DÖNEMDE ANALİZ EDİLECEK PERSONELLER
    # =========================================================

    def get_period_scores(self):
        """
        Yalnızca ilgili dönem için nihai skoru
        hesaplanmış personeller analiz edilir.
        """

        return (
            EmployeePeriodScore.objects
            .filter(period=self.period)
            .select_related("employee", "period")
            .order_by("employee__first_name", "employee__last_name")
        )

    # =========================================================
    # TEK PERSONEL
    # =========================================================

    def generate_for_employee(self, employee):
        service = UpgradeRecommendationService(
            employee=employee,
            period=self.period,
            rule=self.rule,
        )

        return service.generate()

    # =========================================================
    # TÜM DÖNEM
    # =========================================================

    def generate_all(self):

        results = {
            "total": 0,
            "generated": 0,
            "skipped": 0,
            "failed": 0,
            "status_counts": {
                "INSUFFICIENT_DATA": 0,
                "WATCH": 0,
                "CANDIDATE": 0,
                "STRONG": 0,
            },
            "recommendations": [],
            "errors": [],
        }

        for period_score in self.get_period_scores():
            results["total"] += 1
            employee = period_score.employee

            try:
                recommendation = self.generate_for_employee(employee)

                # En yüksek seviyedeki personelde
                # service.generate() None dönebilir.
                if recommendation is None:
                    results["skipped"] += 1
                    continue

                results["generated"] += 1

                if recommendation.status in results["status_counts"]:
                    results["status_counts"][recommendation.status] += 1

                results["recommendations"].append(recommendation)

            except UpgradeRecommendationError as exc:
                results["failed"] += 1
                results["errors"].append({
                    "employee_id": employee.pk,
                    "employee": str(employee),
                    "error": str(exc),
                })

        return results