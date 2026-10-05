from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from apps.accounts.forms import UserPasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard:index")


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy("accounts:password_change_done")


class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"
