from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from django.views.generic import DetailView, ListView
from apps.employees.models import Employee
from apps.employees.services.compensation import EmployeeCompensationService
from apps.employees.services.experience import EmployeeExperienceService
from apps.employees.services.visibility import EmployeeVisibilityService
from apps.scoring.models import EmployeePeriodScore, JobLevelRate


class EmployeeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Employee
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    permission_required = "employees.view_employee"
    paginate_by = 5

    def get_queryset(self):
        queryset = EmployeeVisibilityService(self.request.user).get_visible_employees()
        search = self.request.GET.get("q", "").strip()

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(personnel_no__icontains=search)
            )

        return queryset.order_by("first_name", "last_name")


class EmployeeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Employee
    template_name = "employees/employee_detail.html"
    context_object_name = "employee"
    permission_required = "employees.view_employee"

    def get_object(self, queryset=None):
        employee = super().get_object(queryset)
        visibility_service = EmployeeVisibilityService(self.request.user)

        if not visibility_service.can_view(employee):
            raise Http404("Personel bulunamadı.")

        return employee

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object

        # ==================================
        # Servisler
        # ==================================
        experience_service = EmployeeExperienceService(employee)
        compensation_service = EmployeeCompensationService(employee)

        # ==================================
        # Güncel organizasyon / görev
        # ==================================
        current_unit = employee.current_unit
        current_title = employee.current_title
        current_management_level = employee.current_management_level
        current_job_role = employee.current_job_role
        current_level_record = employee.current_level_record
        current_level = current_level_record.level if current_level_record else None

        # ==================================
        # Güncel günlük ücret
        # ==================================
        current_daily_rate = None

        if current_job_role and current_level:
            today = timezone.localdate()

            current_daily_rate = (
                JobLevelRate.objects
                .filter(job_role=current_job_role, level=current_level, active=True, valid_from__lte=today)
                .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
                .order_by("-valid_from", "-pk")
                .first()
            )

        # ==================================
        # Son upgrade
        # ==================================
        last_upgrade = (
            employee.upgrades
            .select_related("from_job_role", "to_job_role", "from_level", "to_level", "period_score")
            .order_by("-effective_date", "-pk")
            .first()
        )

        # ==================================
        # Upgrade geçmişi
        # ==================================
        upgrades = (
            employee.upgrades
            .select_related("from_job_role", "to_job_role", "from_level", "to_level", "period_score")
            .order_by("-effective_date", "-pk")
        )

        # ==================================
        # Context
        # ==================================
        context.update({

            # ------------------------------
            # Güncel bilgiler
            # ------------------------------
            "current_unit": current_unit,
            "current_title": current_title,
            "current_management_level": current_management_level,
            "current_job_role": current_job_role,
            "current_level": current_level,
            "current_daily_rate": current_daily_rate,

            # ------------------------------
            # Eğitim
            # ------------------------------
            "educations":
                employee.educations
                .select_related("education_level")
                .order_by("-is_primary_for_scoring", "-graduation_date"),

            # ------------------------------
            # Departman geçmişi
            # ------------------------------
            "department_history": employee.department_history.select_related("department", "unit").order_by("-start_date"),

            # ------------------------------
            # Unvan geçmişi
            # ------------------------------
            "title_history":employee.title_history.select_related("job_title").order_by("-start_date"),

            # ------------------------------
            # İş kolu geçmişi
            # ------------------------------
            "assignment_history": employee.assignments.select_related("job_role").order_by("-start_date"),

            # ------------------------------
            # Kariyer seviyesi geçmişi
            # ------------------------------
            "level_history": employee.level_history.select_related("job_role", "level").order_by("-start_date"),

            # ------------------------------
            # Upgrade
            # ------------------------------
            "upgrades": upgrades,
            "last_upgrade": last_upgrade,
            # ------------------------------
            # Ücret geçmişi
            # ------------------------------
            "compensation_history": compensation_service.get_history(),

            # ------------------------------
            # Nihai skorlar
            # ------------------------------
            "period_scores":
                EmployeePeriodScore.objects
                .filter(employee=employee)
                .select_related("period", "formula")
                .prefetch_related("components", "components__component")
                .order_by("-period__start_date"),

            # ------------------------------
            # Deneyim
            # ------------------------------
            "institution_experience": experience_service.get_institution(),
            "professional_experience": experience_service.get_professional(),
            "it_experience": experience_service.get_it(),
        })

        return context
