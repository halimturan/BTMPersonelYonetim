from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from apps.employees.services.visibility import EmployeeVisibilityService
from apps.performance.models import EvaluationPeriod, PerformanceEvaluationReviewer
from apps.scoring.models import EmployeePeriodScore


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )

        user = self.request.user

        employee = getattr(
            user,
            "employee",
            None,
        )

        visible_employees = (
            EmployeeVisibilityService(
                user
            )
            .get_visible_employees()
        )

        pending_reviews = (
            PerformanceEvaluationReviewer.objects
            .none()
        )

        if employee:
            pending_reviews = (
                PerformanceEvaluationReviewer.objects
                .filter(
                    reviewer_employee=employee,
                    submitted_at__isnull=True,
                )
                .select_related(
                    "evaluation",
                    "evaluation__employee",
                    "evaluation__period",
                )
                .order_by(
                    "evaluation__period__end_date"
                )
            )

        active_period = (
            EvaluationPeriod.objects
            .filter(is_active=True, is_locked=False)
            .annotate(
                evaluation_count=Count("evaluations", distinct=True),
                completed_count=Count("evaluations", filter=Q(evaluations__completed_at__isnull=False), distinct=True),
            )
            .order_by("-start_date")
            .first()
        )

        alerts = []

        if pending_reviews.exists():
            alerts.append({
                "type": "warning",
                "icon": "clipboard-check",
                "title": (
                    f"{pending_reviews.count()} "
                    "bekleyen değerlendirmeniz var"
                ),
                "message": (
                    "Size atanmış performans "
                    "değerlendirmelerini tamamlayın."
                ),
                "url_name":
                    "performance:my_reviews",
            })

        if (active_period and user.has_perm("performance.view_evaluationperiod")):
            incomplete_count = (active_period.evaluation_count - active_period.completed_count)

            if incomplete_count > 0:
                alerts.append({
                    "type": "info",
                    "icon": "hourglass-split",
                    "title": (
                        f"{incomplete_count} "
                        "performans değerlendirmesi "
                        "tamamlanmadı"
                    ),
                    "message":
                        active_period.name,
                    "period_id":
                        active_period.pk,
                })

            score_count = (
                EmployeePeriodScore.objects
                .filter(
                    period=active_period
                )
                .count()
            )

            missing_score_count = max(
                active_period.evaluation_count
                - score_count,
                0,
            )

            if (
                active_period.completed_count
                == active_period.evaluation_count
                and missing_score_count
            ):
                alerts.append({
                    "type": "danger",
                    "icon": "calculator",
                    "title": (
                        f"{missing_score_count} "
                        "personelin nihai skoru eksik"
                    ),
                    "message": (
                        "Skor hesaplamasını çalıştırın "
                        "ve hataları kontrol edin."
                    ),
                    "period_id":
                        active_period.pk,
                })

            today = timezone.localdate()

            if (
                active_period.evaluation_end_date
                and
                active_period.evaluation_end_date >= today
            ):
                days_left = (
                    active_period.evaluation_end_date
                    - today
                ).days

                if days_left <= 7:
                    alerts.append({
                        "type": "warning",
                        "icon": "calendar-event",
                        "title": (
                            "Değerlendirme süresinin "
                            f"bitmesine {days_left} gün kaldı"
                        ),
                        "message":
                            active_period.name,
                        "period_id":
                            active_period.pk,
                    })

        context.update({
            "visible_employee_count":
                visible_employees.count(),

            "pending_review_count":
                pending_reviews.count(),

            "pending_reviews":
                pending_reviews[:5],

            "active_period":
                active_period,

            "alerts":
                alerts,
        })

        return context