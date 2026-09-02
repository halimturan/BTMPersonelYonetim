from django.urls import path
from .views import EmployeeListView, EmployeeDetailView


app_name = "employees"


urlpatterns = [
    path("list/", EmployeeListView.as_view(), name="employee_list"),
    path("detailt/<int:id>/", EmployeeDetailView.as_view(), name="employee_detail"),
]