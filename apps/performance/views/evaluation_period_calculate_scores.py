from apps.scoring.services.period_score_calculator import PeriodScoreCalculator
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from apps.performance.models import EvaluationPeriod


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
