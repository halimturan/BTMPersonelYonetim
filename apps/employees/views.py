from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from apps.employees.models import Employee
from apps.employees.services.visibility import EmployeeVisibilityService


class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = "employees/list.html"
    context_object_name = "employees"
    paginate_by = 25

    def get_queryset(self):
        return (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees()
            .select_related("employment_type")
        )


class EmployeeDetailView(LoginRequiredMixin, DetailView):

    model = Employee
    template_name = "employees/detail.html"
    context_object_name = "employee"

    def get_queryset(self):
        return (
            EmployeeVisibilityService(self.request.user)
            .get_visible_employees()
        )
