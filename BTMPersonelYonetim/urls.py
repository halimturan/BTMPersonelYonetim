from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.web.urls")),
    path("employees/", include("apps.employees.urls")),
    path("performance/", include("apps.performance.urls")),
]
