from django.db import models
from django.conf import settings

class RedDay(models.Model):
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=255, blank=True)
    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='red_days_set',
        limit_choices_to={'role': 'admin'}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date} — {self.reason or 'Holiday'}"

    @classmethod
    def is_red(cls, date):
        """Quick check: returns True if a given date is a red day."""
        return cls.objects.filter(date=date).exists()

    @classmethod
    def red_dates_in_month(cls, year, month):
        """Returns a set of dates marked red in a given month."""
        return set(
            cls.objects.filter(date__year=year, date__month=month)
                       .values_list('date', flat=True)
        )