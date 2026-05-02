from django.db import models

class LessonSlot(models.Model):
    number = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.number} ({self.start_time}-{self.end_time})"