from django.urls import path

from apps.performance.views import (MyReviewDetailView, MyReviewListView)


app_name = "performance"


urlpatterns = [
    path("my-reviews/", MyReviewListView.as_view(), name="my_reviews"),
    path("my-reviews/<int:pk>/", MyReviewDetailView.as_view(), name="my_review_detail",),
]