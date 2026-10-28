from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from apps.performance.forms import EvaluationPeriodForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.performance.models import EvaluationPeriod


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
