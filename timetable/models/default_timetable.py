from django.db import models
from django.conf import settings

class DefaultTimetable(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='default_schedule',
        limit_choices_to={'role': 'teacher'}
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    time_slot   = models.CharField(max_length=20)   # e.g. "08:00-09:30"
    slot_number = models.PositiveSmallIntegerField() # e.g. 1, 2, 3 (lesson number)
    subject     = models.CharField(max_length=200)
    room        = models.CharField(max_length=50, blank=True)
    group       = models.CharField(max_length=100, blank=True)  # student group
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'slot_number']
        unique_together = ['teacher', 'day_of_week', 'slot_number']

    def __str__(self):
        return (
            f"{self.teacher} | "
            f"{self.get_day_of_week_display()} | "
            f"Slot {self.slot_number} | {self.subject}"
        )