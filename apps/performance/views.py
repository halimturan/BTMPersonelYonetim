from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.performance.forms import PerformanceReviewForm
from apps.performance.models import (PerformanceEvaluationReviewer)


class MyReviewListView(LoginRequiredMixin, ListView):
    model = PerformanceEvaluationReviewer

    template_name = "performance/my_review_list.html"
    context_object_name = "reviews"

    paginate_by = 25

    def get_queryset(self):
        employee = getattr(self.request.user, "employee", None)

        if not employee:
            return PerformanceEvaluationReviewer.objects.none()

        return (
            PerformanceEvaluationReviewer.objects
            .filter(
                reviewer_employee=employee,
            )
            .select_related(
                "evaluation",
                "evaluation__employee",
                "evaluation__period",
                "reviewer_role",
            )
            .order_by(
                "-evaluation__period__start_date",
                "evaluation__employee__first_name",
            )
        )


class MyReviewDetailView(
    LoginRequiredMixin,
    FormView,
):
    template_name = "performance/my_review_detail.html"
    form_class = PerformanceReviewForm

    def get_review(self):

        employee = getattr(
            self.request.user,
            "employee",
            None,
        )

        return (
            PerformanceEvaluationReviewer.objects
            .select_related(
                "evaluation",
                "evaluation__employee",
                "evaluation__period",
                "evaluation__template",
                "reviewer_role",
            )
            .prefetch_related(
                "criterion_scores",
                "evaluation__template__criteria__criterion",
            )
            .get(
                pk=self.kwargs["pk"],
                reviewer_employee=employee,
            )
        )

    def dispatch(self, request, *args, **kwargs):

        self.review = self.get_review()

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["reviewer"] = self.review

        return kwargs

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["review"] = self.review

        return context

    def form_valid(self, form):

        form.save()

        messages.success(
            self.request,
            "Değerlendirme kaydedildi.",
        )

        return redirect(
            reverse(
                "performance:my_review_detail",
                kwargs={"pk": self.review.pk},
            )
        )