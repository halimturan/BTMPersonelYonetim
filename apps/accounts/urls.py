from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import UserLoginView, UserPasswordChangeView, UserPasswordChangeDoneView


app_name = "accounts"


urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/change/", UserPasswordChangeView.as_view(), name="password_change"),
    path("password/change/done/", UserPasswordChangeDoneView.as_view(), name="password_change_done"),
]