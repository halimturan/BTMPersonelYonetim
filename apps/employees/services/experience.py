from dateutil.relativedelta import relativedelta
from django.utils import timezone


class EmployeeExperienceService:

    INSTITUTION = "institution"
    PROFESSIONAL = "professional"
    IT = "it"

    def __init__(self, employee, reference_date=None):
        self.employee = employee
        self.reference_date = reference_date or timezone.localdate()

    def _get_experience(self, source_code):
        return (
            self.employee
            .experiences
            .select_related("source")
            .filter(source__code=source_code, start_date__lte=self.reference_date)
            .order_by("start_date")
            .first()
        )

    def _calculate_duration(self, start_date):
        if not start_date:
            return None

        duration = relativedelta(self.reference_date, start_date)

        return {
            "years": duration.years,
            "months": duration.months,
            "days": duration.days,
            "text": self._duration_text(
                duration.years,
                duration.months,
                duration.days,
            ),
        }

    def _duration_text(self, years, months, days):
        parts = []

        if years: parts.append(f"{years} yıl")
        if months: parts.append(f"{months} ay")
        if not parts and days: parts.append(f"{days} gün")

        if not parts:
            return "0 gün"

        return " ".join(parts)

    def get_institution(self):
        return self._get_result(self.INSTITUTION)

    def get_professional(self):
        return self._get_result(self.PROFESSIONAL)

    def get_it(self):
        return self._get_result(self.IT)

    def _get_result(self, source_code):
        experience = self._get_experience(source_code)

        if not experience:
            return None

        return {
            "experience": experience,
            "start_date": experience.start_date,
            "duration": self._calculate_duration(experience.start_date),
        }