# apps/backend/realestate/models/agent.py

"""
Agent - Backend/operational information.
This is internal data used by the system.
"""

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_resized import ResizedImageField

from .base import TimeStampedModel
from .managers import AgentManager


class Agent(TimeStampedModel):
    """
    Operational agent data - not publicly visible.
    Used for internal verification, metrics, and system operations.
    """
    
    agent_profile = models.OneToOneField(
        "realestate.AgentProfile",
        on_delete=models.CASCADE,
        related_name="agent",
    )
    
    # Internal/operational fields
    license_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Professional license number",
    )
    
    license_image = ResizedImageField(
        size=[1200, 1200],
        upload_to="agent_licenses/",
        quality=90,
        blank=True,
        null=True,
        help_text="Image of the professional license",
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the agent's identity and credentials are verified",
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the agent is currently active",
    )
    
    # Performance metrics (cached)
    total_listings = models.PositiveIntegerField(
        default=0,
        help_text="Total number of listings managed",
    )
    
    total_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total value of sales closed",
    )
    
    agent_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average rating from clients (0-5)",
    )
    
    total_reviews = models.PositiveIntegerField(
        default=0,
        help_text="Total number of reviews received",
    )
    
    # Manager
    objects = AgentManager()
    
    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        ordering = ["-created"]
        
        indexes = [
            models.Index(
                fields=["is_verified"],
                name="agent_verified_idx",
            ),
            models.Index(
                fields=["is_active"],
                name="agent_active_idx",
            ),
            models.Index(
                fields=["agent_rating"],
                name="agent_rating_idx",
            ),
            models.Index(
                fields=["total_listings"],
                name="agent_listings_idx",
            ),
        ]
        
        permissions = [
            (
                "can_verify_agent",
                "Can verify agent credentials",
            ),
            (
                "can_deactivate_agent",
                "Can deactivate agent accounts",
            ),
        ]
    
    def __str__(self):
        """Return a human-readable representation of the agent."""
        user = self.user
        
        if user:
            full_name = user.get_full_name()
            if full_name:
                return f"Agent: {full_name}"
            return f"Agent: {user.email}"
        
        return f"Agent: {self.pk}"
    
    @property
    def user(self):
        """Return the associated user through agent_profile."""
        if not self.agent_profile:
            return None
        return self.agent_profile.user
    
    @property
    def display_name(self):
        """Return the best available human-readable agent name."""
        user = self.user
        if not user:
            return "Unknown Agent"
        
        full_name = user.get_full_name()
        if full_name:
            return full_name
        return user.email or str(user)
    
    @property
    def full_name(self):
        """Get the agent's full name from the user model."""
        user = self.user
        return user.get_full_name() if user else None
    
    @property
    def email(self):
        """Get the agent's email from the user model."""
        user = self.user
        return user.email if user else None
    
    def update_metrics(self):
        """
        Recalculate cached agent performance metrics.
        Should be called when transactions or listings change.
        """
        from .listing import Listing
        from .transaction import Transaction
        
        # Update total listings
        self.total_listings = self.listings_agent.count()
        
        # Update total sales
        from django.db.models import Sum
        
        self.total_sales = (
            Transaction.objects
            .filter(
                agent=self,
                status="closed",
            )
            .aggregate(
                total=Sum("agreed_price"),
            )["total"]
            or 0
        )
        
        # Update average rating from agent ratings
        from .agent_rating import AgentRating
        
        avg_rating = (
            AgentRating.objects
            .filter(agent=self)
            .aggregate(
                avg=Sum("rating") / Count("id") if Count("id") > 0 else 0,
            )["avg"]
        )
        
        if avg_rating is not None:
            self.agent_rating = round(avg_rating, 2)
        
        # Update total reviews
        self.total_reviews = AgentRating.objects.filter(agent=self).count()
        
        self.save(
            update_fields=[
                "total_listings",
                "total_sales",
                "agent_rating",
                "total_reviews",
            ],
        )
    
    @classmethod
    def create_from_user(cls, user, **kwargs):
        """
        Create an Agent from an existing User.
        Assumes AgentProfile already exists for the user.
        """
        agent_profile = getattr(
            user,
            "realestate_agent_profile",
            None,
        )
        
        if agent_profile is None:
            raise ValueError(
                "User does not have an agent profile. "
                "Create AgentProfile first."
            )
        
        return cls.objects.create(
            agent_profile=agent_profile,
            **kwargs,
        )