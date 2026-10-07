from decimal import Decimal
from django.db import transaction, models
from apps.employees.models import Employee, EmployeeEducation, EmployeeExperience, EmployeeLevelHistory
from apps.organization.models import CareerLevel
from apps.scoring.models import EmployeePeriodScore, EmployeeUpgradeRecommendation, UpgradeRecommendationRule


class UpgradeRecommendationError(Exception):
    pass


class UpgradeRecommendationService:
    """
    Personelin geçmiş dönem skorlarını, eğitimini,
    tecrübesini ve benzer personellerin kariyer
    seviyelerini inceleyerek upgrade önerisi üretir.
    """

    PROFESSIONAL_EXPERIENCE_CODE = "professional"

    def __init__(
        self,
        employee,
        period,
        rule=None,
    ):
        self.employee = employee
        self.period = period

        self.rule = (
            rule
            or UpgradeRecommendationRule.objects
            .filter(active=True)
            .order_by("-pk")
            .first()
        )

        if not self.rule:
            raise UpgradeRecommendationError(
                "Aktif upgrade öneri kuralı bulunamadı."
            )

    # =========================================================
    # DÖNEM TARİHİ
    # =========================================================

    def get_reference_date(self):
        """
        Öneri, ilgili dönemin sonundaki personel
        durumuna göre oluşturulur.
        """

        return self.period.end_date

    # =========================================================
    # MEVCUT İŞ KOLU / SEVİYE
    # =========================================================

    def get_level_record(self, employee=None):
        employee = employee or self.employee
        reference_date = self.get_reference_date()

        return (
            EmployeeLevelHistory.objects
            .filter(
                employee=employee,
                start_date__lte=reference_date,
            )
            .filter(
                models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=reference_date)
            )
            .select_related(
                "job_role",
                "level",
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

    # =========================================================
    # SONRAKİ SEVİYE
    # =========================================================

    def get_next_level(self, current_level):
        return (
            CareerLevel.objects
            .filter(
                active=True,
                order__gt=current_level.order,
            )
            .order_by("order")
            .first()
        )

    # =========================================================
    # PERFORMANS GEÇMİŞİ
    # =========================================================

    def get_score_history(self):
        """
        Referans dönem dahil olmak üzere personelin
        son N dönem nihai skorunu getirir.
        """

        return list(
            EmployeePeriodScore.objects
            .filter(
                employee=self.employee,
                period__end_date__lte=self.period.end_date,
            )
            .select_related("period")
            .order_by(
                "-period__end_date",
                "-pk",
            )[:self.rule.min_period_count]
        )

    def get_performance_analysis(self):
        scores = self.get_score_history()

        values = [
            Decimal(str(item.final_score))
            for item in scores
        ]

        if not values:
            return {
                "period_count": 0,
                "average_score": None,
                "minimum_score": None,
                "enough_periods": False,
                "average_passed": False,
                "minimum_passed": False,
                "passed": False,
                "periods": [],
            }

        average_score = (
            sum(values) / Decimal(len(values))
        )

        minimum_score = min(values)

        enough_periods = (
            len(values)
            >= self.rule.min_period_count
        )

        average_passed = (
            average_score
            >= self.rule.min_average_score
        )

        minimum_passed = (
            minimum_score
            >= self.rule.min_period_score
        )

        return {
            "period_count":
                len(values),

            "average_score":
                average_score,

            "minimum_score":
                minimum_score,

            "enough_periods":
                enough_periods,

            "average_passed":
                average_passed,

            "minimum_passed":
                minimum_passed,

            "passed": (
                enough_periods
                and average_passed
                and minimum_passed
            ),

            "periods": [
                {
                    "period_id": item.period_id,
                    "period": str(item.period),
                    "score": float(item.final_score),
                }
                for item in scores
            ],
        }

    # =========================================================
    # EĞİTİM
    # =========================================================

    def get_primary_education(self, employee=None):
        employee = employee or self.employee

        return (
            EmployeeEducation.objects
            .filter(
                employee=employee,
                is_primary_for_scoring=True,
            )
            .select_related("education_level")
            .first()
        )

    # =========================================================
    # TECRÜBE
    # =========================================================

    def get_professional_experience_record(
        self,
        employee=None,
    ):
        employee = employee or self.employee

        return (
            EmployeeExperience.objects
            .filter(
                employee=employee,
                source__code=(
                    self.PROFESSIONAL_EXPERIENCE_CODE
                ),
            )
            .select_related("source")
            .order_by("start_date")
            .first()
        )

    def get_experience_years(
        self,
        employee=None,
    ):
        record = (
            self.get_professional_experience_record(
                employee
            )
        )

        if not record:
            return None

        reference_date = self.get_reference_date()

        start_date = record.start_date

        if start_date > reference_date:
            return None

        effective_end = (
            record.end_date
            if (
                record.end_date
                and record.end_date < reference_date
            )
            else reference_date
        )

        days = (
            effective_end - start_date
        ).days

        return Decimal(days) / Decimal("365.25")

    # =========================================================
    # BENZER PERSONEL
    # =========================================================

    def get_peer_candidates(
        self,
        current_record,
    ):
        """
        İlk filtre:
        - aktif personel
        - aynı iş kolu
        - kendisi hariç

        Seviye, eğitim ve tecrübe kontrolleri
        Python tarafında yapılır çünkü referans
        tarihe göre geçmiş kayıt okunmaktadır.
        """

        employee_ids = (
            EmployeeLevelHistory.objects
            .filter(
                job_role=current_record.job_role,
                start_date__lte=self.get_reference_date(),
            )
            .filter(
                models.Q(end_date__isnull=True)
                | models.Q(
                    end_date__gte=self.get_reference_date()
                )
            )
            .exclude(
                employee=self.employee,
            )
            .values_list(
                "employee_id",
                flat=True,
            )
        )

        return (
            Employee.objects
            .filter(
                pk__in=employee_ids,
                is_active=True,
            )
            .distinct()
        )

    def get_similar_peers(
        self,
        current_record,
    ):
        own_education = (
            self.get_primary_education()
        )

        own_experience = (
            self.get_experience_years()
        )

        if not own_education:
            return []

        if own_experience is None:
            return []

        tolerance = Decimal(
            str(
                self.rule
                .experience_tolerance_years
            )
        )

        peers = []

        for peer in self.get_peer_candidates(
            current_record
        ):
            peer_record = (
                self.get_level_record(peer)
            )

            if not peer_record:
                continue

            # Aynı iş kolunda olmalı.
            if (
                peer_record.job_role_id
                != current_record.job_role_id
            ):
                continue

            peer_education = (
                self.get_primary_education(peer)
            )

            if not peer_education:
                continue

            # İlk sürümde aynı eğitim seviyesi.
            if (
                peer_education.education_level_id
                != own_education.education_level_id
            ):
                continue

            peer_experience = (
                self.get_experience_years(peer)
            )

            if peer_experience is None:
                continue

            difference = abs(
                peer_experience
                - own_experience
            )

            if difference > tolerance:
                continue

            peer_score = (
                EmployeePeriodScore.objects
                .filter(
                    employee=peer,
                    period__end_date__lte=(
                        self.period.end_date
                    ),
                )
                .order_by(
                    "-period__end_date",
                    "-pk",
                )
                .first()
            )

            peers.append({
                "employee": peer,
                "level_record": peer_record,
                "education": peer_education,
                "experience_years":
                    peer_experience,
                "latest_score": peer_score,
            })

        return peers

    # =========================================================
    # AKRAN ANALİZİ
    # =========================================================

    def get_peer_analysis(
        self,
        current_record,
    ):
        peers = self.get_similar_peers(
            current_record
        )

        higher_peers = [
            peer
            for peer in peers
            if (
                peer["level_record"].level.order
                > current_record.level.order
            )
        ]

        peer_count = len(peers)
        higher_count = len(higher_peers)

        if peer_count:
            higher_ratio = (
                Decimal(higher_count)
                / Decimal(peer_count)
                * Decimal("100")
            )
        else:
            higher_ratio = Decimal("0")

        peer_scores = [
            Decimal(
                str(
                    peer["latest_score"]
                    .final_score
                )
            )
            for peer in peers
            if peer["latest_score"]
        ]

        peer_average_score = None

        if peer_scores:
            peer_average_score = (
                sum(peer_scores)
                / Decimal(len(peer_scores))
            )

        return {
            "peer_count": peer_count,

            "higher_level_peer_count":
                higher_count,

            "higher_level_peer_ratio":
                higher_ratio,

            "peer_average_score":
                peer_average_score,

            "enough_peers": (
                peer_count
                >= self.rule.min_peer_count
            ),

            "peers": peers,
        }

    # =========================================================
    # ÖNERİ PUANI
    # =========================================================

    def calculate_recommendation_score(
        self,
        performance,
        peer_analysis,
    ):
        """
        İlk sürüm:

        Performans geçmişi : %60
        Akran karşılaştırma : %40

        Buradaki eğitim ve tecrübe zaten akran
        grubunu oluştururken filtre olarak kullanılır.
        """

        performance_score = (
            performance["average_score"]
            or Decimal("0")
        )

        peer_score = min(
            peer_analysis[
                "higher_level_peer_ratio"
            ],
            Decimal("100"),
        )

        result = (
            performance_score
            * Decimal("0.60")
            +
            peer_score
            * Decimal("0.40")
        )

        return result.quantize(
            Decimal("0.01")
        )

    # =========================================================
    # STATÜ
    # =========================================================

    def determine_status(
        self,
        performance,
        peer_analysis,
    ):
        # Performans temel şartlarını sağlamıyorsa
        # upgrade adayı değildir.

        if not performance["passed"]:
            return (
                EmployeeUpgradeRecommendation
                .Status.WATCH
            )

        # Yeterli akran yoksa güçlü bir
        # karşılaştırma yapamayız.

        if not peer_analysis["enough_peers"]:
            return (
                EmployeeUpgradeRecommendation
                .Status.WATCH
            )

        ratio = (
            peer_analysis[
                "higher_level_peer_ratio"
            ]
        )

        if (
            ratio
            >= self.rule.strong_peer_ratio
        ):
            return (
                EmployeeUpgradeRecommendation
                .Status.STRONG
            )

        if (
            ratio
            >= self.rule.candidate_peer_ratio
        ):
            return (
                EmployeeUpgradeRecommendation
                .Status.CANDIDATE
            )

        return (
            EmployeeUpgradeRecommendation
            .Status.WATCH
        )

    # =========================================================
    # AÇIKLAMA
    # =========================================================

    def build_explanation(
        self,
        current_record,
        next_level,
        performance,
        peer_analysis,
    ):
        education = (
            self.get_primary_education()
        )

        experience_years = (
            self.get_experience_years()
        )

        peers = []

        for peer in peer_analysis["peers"]:

            latest_score = peer["latest_score"]

            peers.append({
                "employee_id":
                    peer["employee"].pk,

                "employee_name":
                    str(peer["employee"]),

                "level":
                    peer[
                        "level_record"
                    ].level.name,

                "level_order":
                    peer[
                        "level_record"
                    ].level.order,

                "experience_years":
                    round(
                        float(
                            peer[
                                "experience_years"
                            ]
                        ),
                        2,
                    ),

                "latest_score": (
                    float(
                        latest_score.final_score
                    )
                    if latest_score
                    else None
                ),
            })

        return {
            "current_job_role":
                current_record.job_role.name,

            "current_level":
                current_record.level.name,

            "recommended_level":
                next_level.name,

            "period_count":
                performance["period_count"],

            "average_score": (
                float(
                    performance[
                        "average_score"
                    ]
                )
                if performance[
                    "average_score"
                ] is not None
                else None
            ),

            "minimum_score": (
                float(
                    performance[
                        "minimum_score"
                    ]
                )
                if performance[
                    "minimum_score"
                ] is not None
                else None
            ),

            "performance_passed":
                performance["passed"],

            "education": (
                education.education_level.name
                if education
                else None
            ),

            "professional_years": (
                round(
                    float(experience_years),
                    2,
                )
                if experience_years
                is not None
                else None
            ),

            "peer_count": peer_analysis["peer_count"],
            "higher_level_peer_count": peer_analysis["higher_level_peer_count"],
            "higher_level_peer_ratio": float(peer_analysis["higher_level_peer_ratio"]),
            "peer_average_score": (
                float(peer_analysis["peer_average_score"])
                if peer_analysis[ "peer_average_score"] is not None else None
            ),
            "periods": performance["periods"],
            "peers": peers,
        }

    # =========================================================
    # ANA ANALİZ
    # =========================================================

    def analyze(self):
        current_record = self.get_level_record()

        if not current_record:
            raise UpgradeRecommendationError("Personelin dönem sonu için iş kolu / seviye kaydı bulunamadı.")

        next_level = self.get_next_level(current_record.level)

        if not next_level:
            return {
                "eligible": False,
                "reason": "Personel zaten en yüksek kariyer seviyesinde.",
            }

        performance = self.get_performance_analysis()
        peer_analysis = self.get_peer_analysis(current_record)
        recommendation_score = self.calculate_recommendation_score(performance, peer_analysis)
        status = self.determine_status(performance, peer_analysis)
        explanation = self.build_explanation(current_record, next_level, performance, peer_analysis)

        return {
            "eligible": True,
            "current_record": current_record,
            "next_level": next_level,
            "performance": performance,
            "peer_analysis": peer_analysis,
            "recommendation_score": recommendation_score,
            "status": status,
            "explanation": explanation,
        }

    # =========================================================
    # KAYDET
    # =========================================================

    @transaction.atomic
    def generate(self):
        analysis = self.analyze()

        if not analysis["eligible"]:
            return None

        current_record = analysis["current_record"]

        recommendation, created = (
            EmployeeUpgradeRecommendation
            .objects
            .update_or_create(
                employee=self.employee,
                period=self.period,
                rule=self.rule,
                defaults={
                    "job_role": current_record.job_role,
                    "current_level": current_record.level,
                    "recommended_level": analysis["next_level"],
                    "recommendation_score": analysis["recommendation_score"],
                    "status": analysis["status"],
                    "explanation": analysis["explanation"],
                },
            )
        )

        return recommendation
# 873 -->