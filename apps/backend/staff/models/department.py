from django.core.exceptions import ValidationError
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=150,)
    code = models.CharField(max_length=50, unique=True,)
    description = models.TextField(blank=True,)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="child_departments",)
    is_active = models.BooleanField(default=True,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        super().clean()

        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A department cannot be its own parent."}
            )
