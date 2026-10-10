from apps.performance.forms import PerformanceReviewForm
from apps.performance.models import PerformanceEvaluationReviewer
from apps.performance.services.submission import ReviewSubmissionError, ReviewSubmissionService
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin


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
