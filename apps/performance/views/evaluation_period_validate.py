from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from apps.performance.services.period_initializer import EvaluationPeriodInitializer
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.performance.models import EvaluationPeriod


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
