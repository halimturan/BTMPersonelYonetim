from django.urls import path

from apps.performance.views import (
    EvaluationPeriodCreateView,
    EvaluationPeriodDetailView,
    EvaluationPeriodInitializeView,
    EvaluationPeriodListView,
    EvaluationPeriodLockView,
    EvaluationPeriodValidateView,
    MyReviewDetailView,
    MyReviewListView,
    EvaluationPeriodCalculateScoresView,
    EvaluationListView,
    PeriodScoreListView,
)

app_name = "performance"

urlpatterns = [
    path(
        "my-reviews/",
        MyReviewListView.as_view(),
        name="my_reviews",
    ),

    path(
        "my-reviews/<int:pk>/",
        MyReviewDetailView.as_view(),
        name="my_review_detail",
    ),

    path(
        "periods/",
        EvaluationPeriodListView.as_view(),
        name="period_list",
    ),

    path(
        "periods/new/",
        EvaluationPeriodCreateView.as_view(),
        name="period_create",
    ),

    path(
        "periods/<int:pk>/",
        EvaluationPeriodDetailView.as_view(),
        name="period_detail",
    ),

    path(
        "periods/<int:pk>/validate/",
        EvaluationPeriodValidateView.as_view(),
        name="period_validate",
    ),

    path(
        "periods/<int:pk>/initialize/",
        EvaluationPeriodInitializeView.as_view(),
        name="period_initialize",
    ),

    path(
        "periods/<int:pk>/lock/",
        EvaluationPeriodLockView.as_view(),
        name="period_lock",
    ),
    path(
        "periods/<int:pk>/calculate-scores/",
        EvaluationPeriodCalculateScoresView.as_view(),
        name="period_calculate_scores",
    ),
    path(
        "evaluations/",
        EvaluationListView.as_view(),
        name="evaluation_list",
    ),
    path(
        "periods/<int:period_pk>/scores/",
        PeriodScoreListView.as_view(),
        name="period_score_list",
    ),
]