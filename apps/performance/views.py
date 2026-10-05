from django.shortcuts import get_object_or_404

from apps.performance.forms import PerformanceReviewForm
from apps.performance.models import PerformanceEvaluationReviewer
from apps.performance.services.submission import ReviewSubmissionError, ReviewSubmissionService
from apps.scoring.services.period_score_calculator import PeriodScoreCalculator
from apps.scoring.models import EmployeePeriodScore

from apps.performance.models import PerformanceEvaluation
from apps.performance.services.visibility import PerformanceEvaluationVisibilityService

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.performance.forms import EvaluationPeriodForm
from apps.performance.models import EvaluationPeriod
from apps.performance.services.period_initializer import EvaluationPeriodInitializer, PeriodInitializationError


class MyReviewListView(LoginRequiredMixin, ListView):
    template_name = "performance/my_review_list.html"
    context_object_name = "reviews"
    paginate_by = 6

    def get_queryset(self):
        employee = getattr(self.request.user, "employee", None)

        if not employee:
            return PerformanceEvaluationReviewer.objects.none()

        queryset = (
            PerformanceEvaluationReviewer.objects
            .filter(reviewer_employee=employee)
            .select_related("evaluation", "evaluation__employee", "evaluation__period", "reviewer_role")
            .order_by("submitted_at", "-evaluation__period__start_date")
        )

        status = self.request.GET.get("status")

        if status == "pending":
            queryset = queryset.filter(submitted_at__isnull=True)

        elif status == "completed":
            queryset = queryset.filter(submitted_at__isnull=False)

        return queryset


class MyReviewDetailView(LoginRequiredMixin, DetailView):
    model = PerformanceEvaluationReviewer
    template_name = "performance/my_review_detail.html"
    context_object_name = "review"

    def get_queryset(self):
        employee = getattr(self.request.user, "employee", None)

        if not employee:
            return PerformanceEvaluationReviewer.objects.none()

        return (
            PerformanceEvaluationReviewer.objects
            .filter(reviewer_employee=employee)
            .select_related("evaluation", "evaluation__employee", "evaluation__period", "evaluation__template", "reviewer_role")
            .prefetch_related("criterion_scores")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        review = self.object
        form = kwargs.get("form")

        if form is None:
            form = PerformanceReviewForm(reviewer=review)

        current_level = review.reviewer_employee.current_management_level

        if current_level:
            previous_reviews = (
                review.evaluation.reviewers
                .exclude(pk=review.pk)
                .filter(
                    reviewer_employee__current_management_level__order__lt=current_level.order,
                    submitted_at__isnull=False,
                )
                .select_related(
                    "reviewer_employee",
                    "reviewer_employee__current_management_level",
                    "reviewer_role",
                )
                .prefetch_related("criterion_scores__criterion")
                .order_by("reviewer_employee__current_management_level__order")
            )
        else:
            previous_reviews = review.evaluation.reviewers.none()

        context["form"] = form
        context["criterion_rows"] = form.get_criterion_rows()
        context["missing_criteria"] = ReviewSubmissionService(review).get_missing_required_criteria()
        context["previous_reviews"] = previous_reviews

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        review = self.object

        if review.submitted_at:
            messages.warning(request,"Bu değerlendirme daha önce gönderilmiş.")
            return redirect("performance:my_review_detail", pk=review.pk)

        form = PerformanceReviewForm(request.POST, reviewer=review)

        if not form.is_valid():
            messages.error(request,"Formda hatalı veya eksik alanlar var.")
            context = self.get_context_data(form=form)
            return self.render_to_response(context)

        action = request.POST.get("action")

        service = ReviewSubmissionService(review)

        try:
            if action == "submit":
                service.submit(form.cleaned_data)
                messages.success(request, "Değerlendirme başarıyla gönderildi.")

            else:
                service.save_draft(form.cleaned_data)
                messages.success(request, "Değerlendirme taslak olarak kaydedildi.")

        except ReviewSubmissionError as exc:
            messages.error(request, str(exc))

        return redirect("performance:my_review_detail", pk=review.pk)


class EvaluationPeriodListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EvaluationPeriod
    template_name = "performance/period_list.html"
    context_object_name = "periods"
    permission_required = "performance.view_evaluationperiod"

    paginate_by = 20

    def get_queryset(self):
        return (
            EvaluationPeriod.objects
            .annotate(
                evaluation_count=Count("evaluations", distinct=True),
                completed_count=Count("evaluations", filter=Q(evaluations__completed_at__isnull=False), distinct=True),
            )
            .order_by("-start_date")
        )


class EvaluationPeriodCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = EvaluationPeriod
    form_class = EvaluationPeriodForm
    template_name = "performance/period_form.html"
    permission_required = "performance.add_evaluationperiod"

    def form_valid(self, form):
        messages.success(self.request,"Değerlendirme dönemi oluşturuldu.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("performance:period_detail", kwargs={"pk": self.object.pk})


class EvaluationPeriodDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = EvaluationPeriod
    template_name = "performance/period_detail.html"
    context_object_name = "period"
    permission_required = "performance.view_evaluationperiod"

    def get_queryset(self):
        return (
            EvaluationPeriod.objects
            .annotate(
                evaluation_count=Count("evaluations", distinct=True),
                completed_count=Count(
                    "evaluations",
                    filter=Q(evaluations__completed_at__isnull=False),
                    distinct=True,
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.object

        evaluations = (
            period.evaluations
            .select_related("employee", "status", "template")
            .prefetch_related("reviewers")
            .order_by("employee__first_name", "employee__last_name")
        )

        context["evaluations"] = evaluations[:100]

        context["reviewer_count"] = sum(evaluation.reviewers.count() for evaluation in evaluations)

        if period.evaluation_count:
            context["completion_percentage"] = round(period.completed_count / period.evaluation_count * 100, 1)
        else:
            context["completion_percentage"] = 0

        validation_key = f"period_validation_{period.pk}"

        context["validation"] = self.request.session.get(validation_key)

        score_count = EmployeePeriodScore.objects.filter(period=period).count()

        context["score_count"] = score_count

        context["score_missing_count"] = max(period.evaluation_count - score_count, 0)

        context["score_result"] = self.request.session.get(f"period_score_result_{period.pk}")

        context["all_evaluations_completed"] = (0 < period.evaluation_count == period.completed_count)
        context["all_scores_calculated"] = (0 < period.evaluation_count == score_count)

        return context


class EvaluationPeriodValidateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "performance.change_evaluationperiod"

    def post(self, request, pk):
        period = EvaluationPeriod.objects.get(pk=pk)
        initializer = EvaluationPeriodInitializer(period)
        result = initializer.validate()

        request.session[f"period_validation_{period.pk}"] = {
            "valid": result.valid,
            "employee_count": result.employee_count,
            "ready_count": result.ready_count,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "issues": [
                {
                    "employee_id": issue.employee_id,
                    "personnel_no": issue.personnel_no,
                    "employee_name": issue.employee_name,
                    "message": issue.message,
                    "severity": issue.severity,
                }
                for issue in result.issues
            ],
        }

        if result.valid:
            messages.success(request,f"Ön kontrol tamamlandı. {result.ready_count} personel değerlendirmeye hazır.")
        else:
            messages.error(request,f"Ön kontrolde {result.error_count} hata bulundu.")

        return redirect("performance:period_detail", pk=period.pk)


class EvaluationPeriodInitializeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "performance.change_evaluationperiod"

    def post(self, request, pk):
        period = EvaluationPeriod.objects.get(pk=pk)

        initializer = EvaluationPeriodInitializer(period)

        try:
            result = initializer.initialize()

        except PeriodInitializationError as exc:
            messages.error(request, str(exc))
            return redirect("performance:period_detail", pk=period.pk)

        request.session.pop(f"period_validation_{period.pk}", None)
        messages.success(request, f"{result['created_count']} personel için değerlendirme oluşturuldu.")

        if result["existing_count"]:
            messages.info(request,f"{result['existing_count']} değerlendirme zaten vardı.")

        return redirect("performance:period_detail", pk=period.pk)


class EvaluationPeriodLockView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "performance.change_evaluationperiod"

    def post(self, request, pk):
        period = get_object_or_404(EvaluationPeriod, pk=pk)

        if period.is_locked:
            messages.info(request,"Bu dönem zaten kilitli.")
            return redirect("performance:period_detail", pk=period.pk)

        evaluation_count = period.evaluations.count()

        if evaluation_count == 0:
            messages.error(request,"Değerlendirme kaydı olmayan bir dönem kilitlenemez.")
            return redirect("performance:period_detail", pk=period.pk)

        incomplete_count = period.evaluations.filter(completed_at__isnull=True).count()

        if incomplete_count:
            messages.error(request,f"{incomplete_count} personelin performans değerlendirmesi henüz tamamlanmadı.")
            return redirect("performance:period_detail", pk=period.pk)

        score_count = EmployeePeriodScore.objects.filter(period=period).count()

        if score_count != evaluation_count:
            missing = evaluation_count - score_count

            messages.error(request,f"{missing} personelin nihai skoru henüz hesaplanmadı. Dönem kilitlenemez.")

            return redirect("performance:period_detail", pk=period.pk)

        period.is_locked = True
        period.is_active = False

        period.save(update_fields=["is_locked", "is_active", "updated_at"])

        messages.success(request,"Tüm değerlendirmeler ve nihai skorlar tamamlandı. Dönem kilitlendi.")

        return redirect("performance:period_detail", pk=period.pk)


class EvaluationPeriodCalculateScoresView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "performance.change_evaluationperiod"

    def post(self, request, pk):
        period = get_object_or_404(EvaluationPeriod, pk=pk)

        if period.is_locked:
            messages.error(request,"Kilitli dönemde skor hesaplanamaz.")
            return redirect("performance:period_detail", pk=period.pk)

        calculator = PeriodScoreCalculator(period)
        result = calculator.calculate()

        request.session[f"period_score_result_{period.pk}"] = {
            "employee_count": result.employee_count,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "valid": result.valid,
            "issues": [
                {
                    "employee_id": issue.employee_id,
                    "employee_name": issue.employee_name,
                    "personnel_no": issue.personnel_no,
                    "message": issue.message,
                }
                for issue in result.issues
            ],
        }

        if result.valid:
            messages.success(request,f"{result.success_count} personelin nihai skoru başarıyla hesaplandı.")

        else:
            messages.warning(
                request,
                (
                    f"{result.success_count} personel başarıyla hesaplandı. "
                    f"{result.error_count} personelde hata bulundu."
                ),
            )

        return redirect("performance:period_detail", pk=period.pk)


class EvaluationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PerformanceEvaluation
    template_name = "performance/evaluation_list.html"
    context_object_name = "evaluations"
    permission_required = "performance.view_performanceevaluation"
    paginate_by = 6

    def get_queryset(self):
        queryset = (
            PerformanceEvaluationVisibilityService(
                self.request.user
            )
            .get_visible_evaluations()
            .select_related(
                "employee",
                "employee__current_management_level",
                "period",
                "status",
                "template",
            )
            .prefetch_related(
                "reviewers",
                "reviewers__reviewer_employee",
                "reviewers__reviewer_employee__current_management_level",
                "reviewers__reviewer_role",
            )
        )

        # ==================================
        # Durum filtresi
        # ==================================

        status = self.request.GET.get("status", "").strip()

        if status == "pending":
            queryset = queryset.filter(completed_at__isnull=True)

        elif status == "completed":
            queryset = queryset.filter(completed_at__isnull=False)

        # status yoksa:
        # Tümü

        return queryset.order_by(
            "-period__start_date",
            "employee__first_name",
            "employee__last_name",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluation_rows = []

        for evaluation in context["evaluations"]:

            chief_review = None
            assistant_manager_review = None
            manager_review = None

            for review in evaluation.reviewers.all():
                reviewer_employee = review.reviewer_employee

                if not reviewer_employee:
                    continue

                level = reviewer_employee.current_management_level

                if not level:
                    continue

                if level.order == 20:
                    chief_review = review

                elif level.order == 30:
                    assistant_manager_review = review

                elif level.order == 40:
                    manager_review = review

            evaluation_rows.append({
                "evaluation": evaluation,
                "chief_review": chief_review,
                "assistant_manager_review": assistant_manager_review,
                "manager_review": manager_review,
            })

        context["evaluation_rows"] = evaluation_rows

        return context

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from apps.performance.models import EvaluationPeriod
from apps.employees.services.visibility import (
    EmployeeVisibilityService,
)
from apps.scoring.models import EmployeePeriodScore


class PeriodScoreListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EmployeePeriodScore
    template_name = "performance/period_score_list.html"
    context_object_name = "scores"
    permission_required = "scoring.view_employeeperiodscore"
    paginate_by = 7

    def dispatch(self, request, *args, **kwargs):
        self.period = get_object_or_404(EvaluationPeriod, pk=kwargs["period_pk"])

        return super().dispatch(request,*args, **kwargs)

    def get_queryset(self):

        visible_employee_ids = (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees()
            .values_list("pk", flat=True)
        )

        return (
            EmployeePeriodScore.objects
            .filter(period=self.period, employee_id__in=visible_employee_ids)
            .select_related("employee", "period", "formula")
            .prefetch_related("components", "components__component")
            .order_by("employee__first_name", "employee__last_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []

        for score in context["scores"]:

            components = {
                item.component.code: item for item in score.components.all()
            }

            rows.append({
                "score": score,
                "education": components.get("EDUCATION"),
                "job_role": components.get("JOB_ROLE"),
                "experience": components.get("EXPERIENCE"),
                "performance": components.get("PERFORMANCE"),
            })

        context.update({
            "period": self.period, "score_rows": rows
        })

        return context