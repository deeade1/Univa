from django.db import models

class Position(models.Model):
    title = models.CharField(max_length=150,)
    code = models.CharField(max_length=50, unique=True,)
    department = models.ForeignKey("staff.Department", on_delete=models.PROTECT, related_name="positions",)
    description = models.TextField(blank=True,)
    is_management = models.BooleanField(default=False,)
    is_active = models.BooleanField(default=True,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)

    class Meta:
        ordering = ["department__name", "title"]
        verbose_name = "Position"
        verbose_name_plural = "Positions"

    def __str__(self):
        return f"{self.title} ({self.code})"

