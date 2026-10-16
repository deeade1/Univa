# apps/backend/realestate/models/agent_profile.py

"""
AgentProfile - Public/profile information.
This is what clients see and what's displayed publicly.
"""

from django.conf import settings
from django.db import models
from django_resized import ResizedImageField


class AgentProfile(models.Model):
    """
    Public-facing agent profile information.
    This is the "business card" of the agent.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="realestate_agent_profile",
        help_text=(
            "PROTECT: users with agent profiles have ongoing "
            "obligations (listings, commissions) and must not be "
            "hard-deleted. Deactivate the account instead."
        ),
    )
    
    # Public information
    company_name = models.CharField(max_length=120, blank=True)
    company_logo = ResizedImageField(
        size=[800, 800],
        upload_to="company_logos/",
        quality=90,
        blank=True,
        null=True,
    )
    bio = models.TextField(blank=True)
    languages = models.JSONField(default=list, blank=True)
    specialization = models.JSONField(default=list, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Agent Profile"
        verbose_name_plural = "Agent Profiles"
    
    def __str__(self):
        return f"Profile: {self.user.email}"