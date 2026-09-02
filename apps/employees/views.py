from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q

from apps.employees.models import Employee
from apps.employees.services.visibility import EmployeeVisibilityService


class EmployeeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Employee

    permission_required = "employees.view_employee"

    template_name = "employees/list.html"
    context_object_name = "employees"

    paginate_by = 25

    def get_queryset(self):
        queryset = (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees(include_self=False)
            .select_related("employment_type")
        )

        search = self.request.GET.get("q", "").strip()

        if search:
            queryset = queryset.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(personnel_no__icontains=search))

        return queryset.order_by("first_name", "last_name")


class EmployeeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Employee

    permission_required = "employees.view_employee"

    template_name = "employees/detail.html"
    context_object_name = "employee"

    def get_queryset(self):
        return (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees(include_self=True)
            .select_related("employment_type")
            .prefetch_related(
                "educations__education_level",
                "assignments__job_role",
                "title_history__job_title",
                "department_history__department",
                "department_history__unit",
                "level_history__level",
                "upgrades__from_level",
                "upgrades__to_level",
                "period_scores",
            )
        )
