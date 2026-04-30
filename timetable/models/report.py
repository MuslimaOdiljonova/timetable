from django.db import models
from django.conf import settings
from .actual_timetable import ActualTimetable

class Report(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewed',  'Reviewed'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
        limit_choices_to={'role': 'teacher'}
    )
    dekan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_reports',
        limit_choices_to={'role': 'dekan'}
    )
    entries = models.ManyToManyField(
        ActualTimetable,
        related_name='reports'
    )

    # The week or period this report covers
    week_start  = models.DateField()
    week_end    = models.DateField()

    status      = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='submitted'
    )
    dekan_note  = models.TextField(blank=True)  # overall feedback from dekan
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['teacher', 'week_start']

    def __str__(self):
        return (
            f"Report | {self.teacher} | "
            f"{self.week_start} → {self.week_end} | {self.status}"
        )

    def approve(self, dekan, note=''):
        from django.utils import timezone
        self.status = 'approved'
        self.dekan = dekan
        self.dekan_note = note
        self.reviewed_at = timezone.now()
        self.save()
        # Cascade: confirm all linked entries
        self.entries.all().update(status='confirmed')

    def reject(self, dekan, note=''):
        from django.utils import timezone
        self.status = 'rejected'
        self.dekan = dekan
        self.dekan_note = note
        self.reviewed_at = timezone.now()
        self.save()