from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from apps.performance.models import EvaluationPeriod
from apps.scoring.models import EmployeePeriodScore


class EvaluationPeriodLockView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "performance.change_evaluationperiod"

    def post(self, request, pk):
        period = get_object_or_404(EvaluationPeriod, pk=pk)

        if period.is_locked:
            messages.info(request,"Bu dönem zaten kilitli.")
            return redirect("performance:period_detail", pk=period.pk)

        evaluation_count = period.evaluations.count()

        if evaluation_count == 0:
            messages.error(request,"Değerlendirme kaydı olmayan bir dönem kilitlenemez.")
            return redirect("performance:period_detail", pk=period.pk)

        incomplete_count = period.evaluations.filter(completed_at__isnull=True).count()

        if incomplete_count:
            messages.error(request,f"{incomplete_count} personelin performans değerlendirmesi henüz tamamlanmadı.")
            return redirect("performance:period_detail", pk=period.pk)

        score_count = EmployeePeriodScore.objects.filter(period=period).count()

        if score_count != evaluation_count:
            missing = evaluation_count - score_count
            messages.error(request,f"{missing} personelin nihai skoru henüz hesaplanmadı. Dönem kilitlenemez.")
            return redirect("performance:period_detail", pk=period.pk)

        period.is_locked = True
        period.is_active = False

        period.save(update_fields=["is_locked", "is_active", "updated_at"])
        messages.success(request,"Tüm değerlendirmeler ve nihai skorlar tamamlandı. Dönem kilitlendi.")
        return redirect("performance:period_detail", pk=period.pk)
