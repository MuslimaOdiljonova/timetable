from django.db import models
from django.conf import settings
from .default_timetable import DefaultTimetable

class ActualTimetable(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('filled',    'Filled'),
        ('confirmed', 'Confirmed'),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='actual_entries',
        limit_choices_to={'role': 'teacher'}
    )
    default_entry = models.ForeignKey(
        DefaultTimetable,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='actual_entries'
    )

    date        = models.DateField()               # specific calendar date
    time_slot   = models.CharField(max_length=20)  # copied from default, editable
    slot_number = models.PositiveSmallIntegerField()
    subject     = models.CharField(max_length=200) # copied from default, editable
    room        = models.CharField(max_length=50, blank=True)
    group       = models.CharField(max_length=100, blank=True)

    status      = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    comment     = models.TextField(blank=True)     # teacher's own note
    dekan_note  = models.TextField(blank=True)     # dekan's feedback comment

    # Audit fields
    filled_at   = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'slot_number']
        unique_together = ['teacher', 'date', 'slot_number']

    def __str__(self):
        return (
            f"{self.teacher} | {self.date} | "
            f"Slot {self.slot_number} | {self.status}"
        )

    def mark_filled(self):
        from django.utils import timezone
        self.status = 'filled'
        self.filled_at = timezone.now()
        self.save()

    def mark_confirmed(self):
        from django.utils import timezone
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save()