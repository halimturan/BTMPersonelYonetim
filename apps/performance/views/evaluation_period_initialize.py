from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from apps.performance.services.period_initializer import EvaluationPeriodInitializer, PeriodInitializationError
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.performance.models import EvaluationPeriod


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
