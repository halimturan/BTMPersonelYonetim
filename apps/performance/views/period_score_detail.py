from apps.performance.models import PerformanceEvaluation
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.employees.services.visibility import EmployeeVisibilityService
from apps.scoring.models import EmployeePeriodScore
from django.http import Http404
from apps.employees.services.experience import EmployeeExperienceService


class PeriodScoreDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = EmployeePeriodScore
    template_name = "performance/period_score_detail.html"
    context_object_name = "period_score"
    permission_required = "scoring.view_employeeperiodscore"

    def get_queryset(self):

        visible_employee_ids = (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees()
            .values_list("pk", flat=True)
        )

        return (
            EmployeePeriodScore.objects
            .filter(employee_id__in=visible_employee_ids)
            .select_related("employee", "period", "formula")
            .prefetch_related("components", "components__component")
        )

    def get_object(self, queryset=None):
        period_score = super().get_object(queryset)

        # URL'deki dönem ile skorun dönemi
        # aynı olmak zorunda.
        if period_score.period_id != self.kwargs["period_pk"]:
            raise Http404("Skor bulunamadı.")
        return period_score

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period_score = self.object

        employee = period_score.employee

        # ==================================
        # Personelin skor açıklama bilgileri
        # ==================================

        primary_education = (
            employee.educations
            .filter(is_primary_for_scoring=True)
            .select_related("education_level")
            .first()
        )

        current_job_role = employee.current_job_role
        experience_service = EmployeeExperienceService(employee)
        professional_experience = experience_service.get_it()

        # ==================================
        # Nihai skor bileşenleri
        # ==================================

        score_components_qs = period_score.components.select_related("component").order_by("component__name")

        score_components = []

        for item in score_components_qs:

            detail_label = None
            detail_value = None

            if item.component.code == "EDUCATION":

                detail_label = "Mezuniyet"

                if primary_education and primary_education.education_level:
                    detail_value = primary_education.education_level.name

            elif item.component.code == "JOB_ROLE":
                detail_label = "İş Kolu"

                if current_job_role:
                    detail_value = current_job_role.name

            elif item.component.code == "EXPERIENCE":
                detail_label = "Tecrübe"

                if professional_experience:
                    detail_value = str(professional_experience.get('duration').get('text'))

            score_components.append({
                "component_score": item,
                "detail_label": detail_label,
                "detail_value": detail_value,
            })

        # ==================================
        # Performans değerlendirmesi
        # ==================================

        evaluation = (
            PerformanceEvaluation.objects
            .filter(
                employee=period_score.employee,
                period=period_score.period,
            )
            .prefetch_related(
                "reviewers",
                "reviewers__reviewer_employee",
                "reviewers__reviewer_employee__current_management_level",
                "reviewers__reviewer_role",
                "reviewers__criterion_scores",
                "reviewers__criterion_scores__criterion",
            )
            .first()
        )

        performance_reviews = []

        if evaluation:

            reviews = list(evaluation.reviewers.all())

            # Yönetim seviyesi sırasına göre:
            # Şef -> Müdür Yrd. -> Müdür

            reviews.sort(
                key=lambda review: (
                    review.reviewer_employee
                    .current_management_level
                    .order
                    if review.reviewer_employee and review.reviewer_employee.current_management_level else 999
                )
            )

            for review in reviews:
                reviewer = review.reviewer_employee
                management_level = reviewer.current_management_level if reviewer else None

                criterion_rows = []

                for criterion_score in (review.criterion_scores.all()):

                    percentage = None
                    if criterion_score.max_score:
                        percentage = round((criterion_score.score / criterion_score.max_score) * 100, 1)

                    criterion_rows.append({
                        "score": criterion_score,
                        "criterion": criterion_score.criterion,
                        "percentage": percentage,
                    })

                performance_reviews.append({
                    "review": review,
                    "reviewer": reviewer,
                    "management_level": management_level,
                    "criterion_rows": criterion_rows,
                })

        context.update({
            "period": period_score.period,
            "employee": period_score.employee,
            "score_components": score_components,
            "evaluation": evaluation,
            "performance_reviews": performance_reviews,
        })

        return context
