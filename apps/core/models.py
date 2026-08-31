from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EffectiveDatedModel(models.Model):
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def is_valid_on(self, date):
        if self.valid_from > date:
            return False

        if self.valid_to and self.valid_to < date:
            return False

        return self.active