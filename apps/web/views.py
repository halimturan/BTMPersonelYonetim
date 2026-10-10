from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.views.generic import TemplateView
from apps.employees.models import EmployeeEducation, EmployeeAssignmentHistory
from apps.employees.services.visibility import EmployeeVisibilityService
from apps.performance.models import EvaluationPeriod, PerformanceEvaluation, PerformanceEvaluationReviewer
from apps.scoring.models import EmployeePeriodScore
from apps.employees.models import EmployeeDepartmentHistory


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index_new.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        employee = getattr(user, "employee", None)

        # ----------------------------------
        # Görüntülenebilir personeller
        # ----------------------------------

        visible_employees = EmployeeVisibilityService(user).get_visible_employees()
        visible_employee_ids = visible_employees.values_list("pk", flat=True)

        # ----------------------------------
        # Cinsiyet dağılımı
        # ----------------------------------
        genders = {
            "erkek": visible_employees.filter(gender="erkek").count(),
            "kadin": visible_employees.filter(gender="kadin").count()
        }

        # ----------------------------------
        # Şeflik dağılımı
        # ----------------------------------
        today = timezone.localdate()
        unit_distribution_qs = (
            EmployeeDepartmentHistory.objects
            .filter(employee_id__in=visible_employee_ids, start_date__lte=today, unit__isnull=False)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .values("unit_id", "unit__name", "unit__icon")
            .annotate(count=Count("employee_id", distinct=True))
            .order_by("-count", "unit__name",)
        )

        unit_distribution = []

        for item in unit_distribution_qs:
            chief = (
                EmployeeDepartmentHistory.objects
                .filter(
                    unit_id=item["unit_id"], start_date__lte=today,
                    employee__is_active=True, employee__current_management_level__order=20,
                )
                .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
                .select_related("employee",)
                .order_by("employee__first_name", "employee__last_name",)
                .first()
            )

            unit_distribution.append({
                "unit_id": item["unit_id"],
                "unit_name": item["unit__name"],
                "unit_icon": item["unit__icon"],
                "count": item["count"],
                "chief": chief.employee if chief else None,
            })

        # ----------------------------------
        # Eğitim dağılımı
        # ----------------------------------

        education_distribution = (
            EmployeeEducation.objects
            .filter(employee_id__in=visible_employee_ids)
            .values("education_level__name")
            .annotate(count=Count("employee_id"))
            .order_by("-count")
        )

        today = timezone.localdate()

        job_role_distribution = (
            EmployeeAssignmentHistory.objects
            .filter(employee_id__in=visible_employee_ids, start_date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            .values("job_role__name")
            .annotate(count=Count("employee_id"))
            .order_by("-count")
        )

        # ----------------------------------
        # Kullanıcının kendi değerlendirmeleri
        # ----------------------------------

        pending_reviews = PerformanceEvaluationReviewer.objects.none()

        if employee:
            pending_reviews = (
                PerformanceEvaluationReviewer.objects
                .filter(reviewer_employee=employee, submitted_at__isnull=True)
                .select_related("evaluation", "evaluation__employee", "evaluation__period")
                .order_by("evaluation__period__end_date")
            )

        # ----------------------------------
        # Aktif dönem
        # ----------------------------------

        active_period = (
            EvaluationPeriod.objects.filter(is_active=True, is_locked=False).order_by("-start_date").first()
        )

        period_evaluations = PerformanceEvaluation.objects.none()
        period_reviewers = PerformanceEvaluationReviewer.objects.none()

        total_evaluations = 0
        completed_evaluations = 0
        incomplete_evaluations = 0
        completion_rate = 0

        average_performance_score = None

        reviewer_progress = []

        # ----------------------------------
        # Aktif dönem istatistikleri
        # ----------------------------------

        if active_period:

            period_evaluations = (
                PerformanceEvaluation.objects.filter(period=active_period, employee_id__in=visible_employee_ids)
            )
            total_evaluations = period_evaluations.count()
            completed_evaluations = period_evaluations.filter(completed_at__isnull=False).count()
            incomplete_evaluations = total_evaluations - completed_evaluations

            if total_evaluations:
                completion_rate = int(round((completed_evaluations / total_evaluations) * 100, 1))

            # ----------------------------------
            # Reviewer görevleri
            # ----------------------------------

            period_reviewers = (
                PerformanceEvaluationReviewer.objects
                .filter(evaluation__in=period_evaluations)
                .select_related(
                    "reviewer_employee",
                    "reviewer_employee__current_management_level",
                    "reviewer_role",
                )
            )

            # ManagementLevel order:
            # Şef = 20
            # Müdür Yardımcısı = 30
            # Müdür = 40

            reviewer_levels = [
                (20, "Şef"),
                (30, "Müdür Yardımcısı"),
                (40, "Müdür")
            ]

            for level_order, level_name in reviewer_levels:
                level_reviews = period_reviewers.filter(reviewer_employee__current_management_level__order=level_order)
                total = level_reviews.count()
                completed = level_reviews.filter(submitted_at__isnull=False).count()
                pending = total - completed
                rate = 0

                if total:
                    rate = round(completed / total * 100, 1)

                reviewer_progress.append({
                    "name": level_name,
                    "total": total,
                    "completed": completed,
                    "pending": pending,
                    "rate": int(rate),
                })

            # ----------------------------------
            # Ortalama performans
            # ----------------------------------

            average_data = period_evaluations.filter(final_performance_score__isnull=False).aggregate(average=Avg("final_performance_score"))
            average_performance_score = average_data["average"]

        # ----------------------------------
        # Alertler
        # ----------------------------------

        alerts = []

        if pending_reviews.exists():

            alerts.append({
                "type": "warning",
                "icon": "abstract-18",
                "title": f"{pending_reviews.count()} bekleyen değerlendirmeniz var",
                "message": "Size atanmış performans değerlendirmelerini tamamlayın.",
                "url_name": "performance:my_reviews",
            })

        if active_period and user.has_perm("performance.view_evaluationperiod"):

            if incomplete_evaluations > 0:
                alerts.append({
                    "type": "info",
                    "icon": "check-circle",
                    "title": f"{incomplete_evaluations} performans değerlendirmesi tamamlanmadı",
                    "message": active_period.name,
                    "period_id": active_period.pk,
                })

            score_count = (
                EmployeePeriodScore.objects
                .filter(period=active_period, employee_id__in=visible_employee_ids)
                .count()
            )

            missing_score_count = max(completed_evaluations - score_count, 0)

            if completed_evaluations > 0 and completed_evaluations == total_evaluations and missing_score_count:

                alerts.append({
                    "type": "danger",
                    "icon": "calculator",
                    "title": f"{missing_score_count} personelin nihai skoru eksik",
                    "message": "Skor hesaplamasını çalıştırın ve hataları kontrol edin.",
                    "period_id": active_period.pk,
                })

            today = timezone.localdate()

            if active_period.evaluation_end_date and active_period.evaluation_end_date >= today:
                days_left = (active_period.evaluation_end_date - today).days

                if days_left <= 7:

                    alerts.append({
                        "type": "warning",
                        "icon": "calendar-event",
                        "title": "Değerlendirme süresinin bitmesine {days_left} gün kaldı",
                        "message": active_period.name,
                        "period_id": active_period.pk,
                    })

        context.update({
            "visible_employee_count": visible_employees.count(),
            "pending_review_count": pending_reviews.count(),
            "pending_reviews": pending_reviews[:5],
            "active_period": active_period,
            "alerts": alerts,
            "total_evaluations": total_evaluations,
            "completed_evaluations": completed_evaluations,
            "incomplete_evaluations": incomplete_evaluations,
            "completion_rate": completion_rate,
            "reviewer_progress": reviewer_progress,
            "average_performance_score": average_performance_score,
            "education_distribution": education_distribution,
            "job_role_distribution":job_role_distribution,
            "genders": genders,
            "unit_distribution": unit_distribution,
        })

        return context