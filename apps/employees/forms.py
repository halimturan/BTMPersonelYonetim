from django import forms
from django.db.models import Q
from apps.employees.models import EmployeeUpgrade


class EmployeeUpgradeAdminForm(forms.ModelForm):

    class Meta:
        model = EmployeeUpgrade

        fields = (
            "employee",
            "to_job_role",
            "to_level",
            "effective_date",
            "reason",
            "period_score",
        )

        widgets = {
            "effective_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        employee = cleaned_data.get(
            "employee"
        )

        to_job_role = cleaned_data.get(
            "to_job_role"
        )

        to_level = cleaned_data.get(
            "to_level"
        )

        effective_date = cleaned_data.get(
            "effective_date"
        )

        if (
            not employee
            or not to_job_role
            or not to_level
            or not effective_date
        ):
            return cleaned_data

        # ======================================
        # Yürürlük tarihindeki mevcut iş kolu
        # ======================================

        assignment = (
            employee.assignments
            .filter(
                start_date__lte=effective_date
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=effective_date
                )
            )
            .select_related(
                "job_role"
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

        if not assignment:
            raise forms.ValidationError(
                (
                    "Personelin yürürlük tarihinde "
                    "geçerli bir iş kolu bulunamadı."
                )
            )

        # ======================================
        # Yürürlük tarihindeki mevcut seviye
        # ======================================

        level_record = (
            employee.level_history
            .filter(
                start_date__lte=effective_date
            )
            .filter(
                Q(end_date__isnull=True)
                | Q(
                    end_date__gte=effective_date
                )
            )
            .select_related(
                "job_role",
                "level",
            )
            .order_by(
                "-start_date",
                "-pk",
            )
            .first()
        )

        if not level_record:
            raise forms.ValidationError(
                (
                    "Personelin yürürlük tarihinde "
                    "geçerli kariyer seviyesi "
                    "bulunamadı."
                )
            )

        # ======================================
        # Mevcut kayıtlar kendi içinde tutarlı mı?
        # ======================================

        if (
            assignment.job_role_id
            != level_record.job_role_id
        ):
            raise forms.ValidationError(
                (
                    "Personelin iş kolu kaydı ile "
                    "kariyer seviye kaydı uyuşmuyor."
                )
            )

        # ======================================
        # Upgrade'a otomatik yaz
        # ======================================

        self.instance.from_job_role = (
            assignment.job_role
        )

        self.instance.from_level = (
            level_record.level
        )

        # ======================================
        # Hiçbir değişiklik yoksa engelle
        # ======================================

        if (
            assignment.job_role_id
            == to_job_role.pk
            and
            level_record.level_id
            == to_level.pk
        ):
            raise forms.ValidationError(
                (
                    "Yeni iş kolu ve yeni seviye "
                    "mevcut değerlerle aynı olamaz."
                )
            )

        # ======================================
        # Aynı iş kolundaysa gerçek upgrade
        # ======================================

        if (
            assignment.job_role_id
            == to_job_role.pk
            and
            to_level.order
            <= level_record.level.order
        ):
            raise forms.ValidationError(
                (
                    "Aynı iş kolunda yeni seviye "
                    "mevcut seviyeden daha yüksek "
                    "olmalıdır."
                )
            )