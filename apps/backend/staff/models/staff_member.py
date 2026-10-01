from django.core.exceptions import ValidationError
from django.db import models

class StaffMember(models.Model):
    class EmploymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        SUSPENDED = "SUSPENDED", "Suspended"
        RESIGNED = "RESIGNED", "Resigned"
        TERMINATED = "TERMINATED", "Terminated"


    user = models.OneToOneField("accounts.User", on_delete=models.PROTECT, related_name="staff_member",)
    employee_number = models.CharField(max_length=50, unique=True,)
    department = models.ForeignKey("staff.Department", on_delete=models.PROTECT, related_name="staff_members",)
    position = models.ForeignKey("staff.Position", on_delete=models.PROTECT, related_name="staff_members",)
    manager = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="direct_reports",)
    employment_status = models.CharField(max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.PENDING,)
    date_joined = models.DateField()
    date_left = models.DateField(null=True, blank=True,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)

    class Meta:
        ordering = ["employee_number"]
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"

    def __str__(self):
        return f"{self.employee_number} - {self.user.get_full_name()}"
    
    def clean(self):
        super().clean()

        if self.manager_id and self.manager_id == self.pk:
            raise ValidationError(
                {"manager": "A staff member cannot be their own manager."}
            )

        if (
            self.date_left
            and self.date_joined
            and self.date_left < self.date_joined
        ):
            raise ValidationError(
                {"date_left": "Date left cannot be before date joined."}
            )

        terminal_statuses = {
            self.EmploymentStatus.RESIGNED,
            self.EmploymentStatus.TERMINATED,
        }

        if self.employment_status in terminal_statuses:
            if self.date_left is None:
                raise ValidationError(
                    {
                        "date_left": (
                            "Date left is required when employment status "
                            "is RESIGNED or TERMINATED."
                        )
                    }
                )
        elif self.date_left is not None:
            raise ValidationError(
                {
                    "date_left": (
                        "Date left must be empty for non-terminal "
                        "employment statuses."
                    )
                }
            )