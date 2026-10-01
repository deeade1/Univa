# apps/backend/ecommerce/models/giftcard.py

"""
Gift Card models.

This module contains the canonical ecommerce gift-card models:

    - GiftCard
    - GiftCardEvent
    - GiftCardTag

Validation functions that are referenced by Django migrations live in
ecommerce.validators.giftcard rather than inside this model module.
"""

import logging
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, BTreeIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import (
    JSONField,
    Q,
    Sum,
    Count,
    F,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.metadata import ModelWithMetadata
from core.pricing import MoneyField

from ecommerce.validators.giftcard import validate_gift_card_code

from .constants import (
    GiftCardEvents,
    GiftCardStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def generate_gift_card_code():
    """
    Generate a cryptographically secure unique-format gift card code.

    Uniqueness itself is enforced by the database.
    """

    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(16)
    )


# =============================================================================
# QUERYSETS & MANAGERS
# =============================================================================

class GiftCardQuerySet(models.QuerySet):
    """Custom queryset for GiftCard model."""
    
    def active(self, date=None):
        """Get active gift cards."""
        if date is None:
            date = timezone.now().date()
        return self.filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gte=date),
            status=GiftCardStatus.ACTIVE,
            is_active=True,
        )
    
    def expired(self, date=None):
        """Get expired gift cards."""
        if date is None:
            date = timezone.now().date()
        return self.filter(
            expiry_date__isnull=False,
            expiry_date__lt=date,
            is_active=True,
        )
    
    def used(self):
        """Get used gift cards."""
        return self.filter(
            Q(status=GiftCardStatus.USED) | Q(status=GiftCardStatus.PARTIALLY_USED)
        )
    
    def by_user(self, user):
        """Get gift cards by user."""
        return self.filter(Q(created_by=user) | Q(used_by=user))
    
    def available(self, user=None):
        """Get available gift cards with balance > 0."""
        queryset = self.active().filter(current_balance_amount__gt=0)
        if user:
            queryset = queryset.filter(used_by=user)
        return queryset
    
    def by_currency(self, currency):
        """Filter by currency."""
        return self.filter(currency=currency)
    
    def search(self, query):
        """Search gift cards."""
        if not query:
            return self
        return self.filter(
            Q(code__icontains=query) |
            Q(created_by_email__icontains=query) |
            Q(used_by_email__icontains=query)
        )
    
    def with_total_balance(self):
        """Annotate with total balance."""
        return self.annotate(total_balance=Sum('current_balance_amount'))
    
    def with_usage_count(self):
        """Annotate with usage count."""
        return self.annotate(usage_count=Count('events'))


class GiftCardManager(models.Manager):
    """Custom manager for GiftCard model."""
    
    def get_queryset(self):
        return GiftCardQuerySet(self.model, using=self._db)
    
    def active(self, date=None):
        return self.get_queryset().active(date)
    
    def expired(self, date=None):
        return self.get_queryset().expired(date)
    
    def used(self):
        return self.get_queryset().used()
    
    def by_user(self, user):
        return self.get_queryset().by_user(user)
    
    def available(self, user=None):
        return self.get_queryset().available(user)
    
    def search(self, query):
        return self.get_queryset().search(query)
    
    def create_gift_card(self, initial_balance, currency, **kwargs):
        """Create a new gift card with generated code."""
        from django.utils.crypto import get_random_string
        
        code = kwargs.pop('code', None)
        if not code:
            code = generate_gift_card_code()
        
        # Ensure code is unique
        while self.filter(code=code).exists():
            code = generate_gift_card_code()
        
        kwargs['code'] = code
        kwargs['initial_balance_amount'] = initial_balance
        kwargs['current_balance_amount'] = initial_balance
        kwargs['currency'] = currency
        
        return self.create(**kwargs)


class GiftCardTagQuerySet(models.QuerySet):
    """Custom queryset for GiftCardTag."""
    
    def search(self, query):
        if not query:
            return self
        return self.filter(name__icontains=query)
    
    def with_card_count(self):
        return self.annotate(card_count=Count('gift_cards'))


class GiftCardTagManager(models.Manager):
    """Custom manager for GiftCardTag."""
    
    def get_queryset(self):
        return GiftCardTagQuerySet(self.model, using=self._db)
    
    def search(self, query):
        return self.get_queryset().search(query)


# =============================================================================
# MODELS
# =============================================================================

class GiftCardTag(models.Model):
    """Tag for categorizing gift cards."""
    
    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Tag name"
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
        help_text="Unique slug for the tag"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the tag"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this tag is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = GiftCardTagManager()

    class Meta:
        ordering = ("name",)
        indexes = [
            BTreeIndex(fields=["name"], name="gift_tag_name_idx"),
            BTreeIndex(fields=["slug"], name="gift_tag_slug_idx"),
            BTreeIndex(fields=["is_active"], name="gift_tag_active_idx"),
            GinIndex(
                name="gift_tag_search_gin",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        return self.name


class GiftCard(ModelWithMetadata):
    """
    Gift Card model.
    
    Tracks gift cards, their balances, and usage.
    """
    
    # Basic Info
    code = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        validators=[MinLengthValidator(8), validate_gift_card_code],
        help_text="Unique gift card code"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this gift card is active"
    )
    status = models.CharField(
        max_length=20,
        choices=GiftCardStatus.CHOICES,
        default=GiftCardStatus.ACTIVE,
        db_index=True,
        help_text="Current status of the gift card"
    )
    
    # Balance
    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        default=os.environ.get("DEFAULT_CURRENCY", "USD"),
        db_index=True,
        help_text="Currency code"
    )
    initial_balance_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Initial balance amount"
    )
    current_balance_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Current balance amount"
    )
    initial_balance = MoneyField(
        amount_field="initial_balance_amount",
        currency_field="currency"
    )
    current_balance = MoneyField(
        amount_field="current_balance_amount",
        currency_field="currency"
    )
    
    # Users
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_gift_cards",
        help_text="User who created the gift card"
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="used_gift_cards",
        help_text="User who used the gift card"
    )
    created_by_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email of the creator (if not a user)"
    )
    used_by_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email of the user who used it (if not a user)"
    )
    
    # Dates
    expiry_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Expiry date of the gift card"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Creation date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update date"
    )
    last_used_on = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the gift card was used"
    )
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the gift card was activated"
    )
    
    # Relationships
    tags = models.ManyToManyField(
        GiftCardTag,
        related_name="gift_cards",
        blank=True,
        help_text="Tags for categorizing"
    )
    product = models.ForeignKey(
        "ecommerce.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gift_cards",
        help_text="Product associated with this gift card"
    )
    fulfillment_line = models.ForeignKey(
        "ecommerce.FulfillmentLine",
        related_name="gift_cards",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Fulfillment line associated with this gift card"
    )
    
    # Search
    search_vector = SearchVectorField(
        blank=True,
        null=True,
        help_text="Search vector for full-text search"
    )
    search_index_dirty = models.BooleanField(
        default=True,
        help_text="Whether the search index needs to be rebuilt"
    )
    
    objects = GiftCardManager()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("code",)
        permissions = (
            ("manage_gift_card", "Manage gift cards."),
            ("view_gift_card_balance", "View gift card balance."),
        )
        indexes = [
            BTreeIndex(fields=["status"], name="giftcard_status_idx"),
            BTreeIndex(fields=["currency"], name="giftcard_currency_idx"),
            BTreeIndex(fields=["expiry_date"], name="giftcard_expiry_idx"),
            BTreeIndex(fields=["last_used_on"], name="giftcard_last_used_idx"),
            BTreeIndex(fields=["is_active", "expiry_date"], name="giftcard_active_expiry_idx"),
            BTreeIndex(fields=["currency", "status"], name="giftcard_currency_status_idx"),
            BTreeIndex(fields=["created_at"], name="giftcard_created_idx"),
            GinIndex(name="giftcard_tsearch", fields=["search_vector"]),
        ]
        
        constraints = [
            models.CheckConstraint(
                condition=Q(initial_balance_amount__gte=0.01),
                name="giftcard_initial_balance_positive"
            ),
            models.CheckConstraint(
                condition=Q(current_balance_amount__gte=0),
                name="giftcard_current_balance_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(initial_balance_amount__gte=F("current_balance_amount")),
                name="giftcard_balance_consistency"
            ),
        ]

    def __str__(self):
        return f"Gift Card {self.display_code} ({self.currency} {self.current_balance_amount})"

    def clean(self):
        """Validate gift card data."""
        if self.initial_balance_amount <= 0:
            raise ValidationError({
                "initial_balance_amount": "Initial balance must be greater than zero."
            })
        
        if self.current_balance_amount < 0:
            raise ValidationError({
                "current_balance_amount": "Current balance cannot be negative."
            })
        
        if self.current_balance_amount > self.initial_balance_amount:
            raise ValidationError({
                "current_balance_amount": "Current balance cannot exceed initial balance."
            })
        
        # Validate expiry date
        if self.expiry_date and self.expiry_date < timezone.now().date():
            if self.status == GiftCardStatus.ACTIVE:
                raise ValidationError({
                    "expiry_date": "Cannot set expiry date in the past for active gift cards."
                })

    def save(self, *args, **kwargs):
        """Save gift card with validation and auto-status update."""
        # Auto-update status based on balance and expiry
        if self.current_balance_amount == 0 and self.status == GiftCardStatus.ACTIVE:
            self.status = GiftCardStatus.USED
        
        if self.expiry_date and self.expiry_date < timezone.now().date():
            if self.status == GiftCardStatus.ACTIVE:
                self.status = GiftCardStatus.EXPIRED
        
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def display_code(self):
        """Display only the last 4 characters of the code."""
        return self.code[-4:] if self.code else ""

    @property
    def is_fully_used(self):
        """Check if the gift card is fully used."""
        return self.current_balance_amount <= 0

    @property
    def is_expired(self):
        """Check if the gift card is expired."""
        return self.expiry_date and self.expiry_date < timezone.now().date()

    @property
    def is_usable(self):
        """Check if the gift card can be used."""
        return (
            self.is_active and
            self.status == GiftCardStatus.ACTIVE and
            self.current_balance_amount > 0 and
            not self.is_expired
        )

    def use_balance(self, amount):
        """
        Use a portion of the gift card balance.
        
        Args:
            amount: Amount to use
            
        Returns:
            bool: True if successful
            
        Raises:
            ValidationError: If insufficient balance or invalid amount
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        
        if not self.is_usable:
            raise ValidationError("Gift card is not usable.")
        
        if amount > self.current_balance_amount:
            raise ValidationError(
                f"Insufficient balance. Available: {self.current_balance_amount}"
            )
        
        self.current_balance_amount -= amount
        self.last_used_on = timezone.now()
        
        if self.current_balance_amount == 0:
            self.status = GiftCardStatus.USED
        
        self.save(update_fields=[
            'current_balance_amount', 'last_used_on', 'status'
        ])
        return True

    def add_balance(self, amount):
        """
        Add balance to the gift card.
        
        Args:
            amount: Amount to add
            
        Returns:
            bool: True if successful
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        
        self.current_balance_amount += amount
        
        # If the card was fully used, reactivate it
        if self.status == GiftCardStatus.USED:
            self.status = GiftCardStatus.ACTIVE
        
        self.save(update_fields=['current_balance_amount', 'status'])
        return True

    def activate(self):
        """Activate the gift card."""
        if self.status != GiftCardStatus.INACTIVE:
            raise ValidationError("Gift card is already active.")
        
        self.is_active = True
        self.status = GiftCardStatus.ACTIVE
        self.activated_at = timezone.now()
        self.save(update_fields=['is_active', 'status', 'activated_at'])

    def deactivate(self):
        """Deactivate the gift card."""
        if self.status == GiftCardStatus.ACTIVE:
            self.is_active = False
            self.status = GiftCardStatus.INACTIVE
            self.save(update_fields=['is_active', 'status'])


class GiftCardEvent(models.Model):
    """
    Gift card event log.
    
    Tracks all actions performed on gift cards.
    """
    
    # Event data
    date = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
        help_text="Event date"
    )
    type = models.CharField(
        max_length=255,
        choices=GiftCardEvents.CHOICES,
        db_index=True,
        help_text="Event type"
    )
    parameters = JSONField(
        blank=True,
        default=dict,
        help_text="Event parameters"
    )
    
    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="gift_card_events",
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who performed the action"
    )
    order = models.ForeignKey(
        "ecommerce.Order",
        null=True,
        on_delete=models.SET_NULL,
        help_text="Order associated with the event"
    )
    gift_card = models.ForeignKey(
        GiftCard,
        related_name="events",
        on_delete=models.CASCADE,
        help_text="Gift card this event belongs to"
    )
    
    # Additional metadata
    amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
        help_text="Amount involved in the event"
    )
    previous_balance = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
        help_text="Balance before the event"
    )
    new_balance = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        null=True,
        blank=True,
        help_text="Balance after the event"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        help_text="User agent string"
    )

    class Meta:
        ordering = ("-date",)
        indexes = [
            BTreeIndex(fields=["gift_card", "date"], name="giftcardevent_card_date_idx"),
            BTreeIndex(fields=["user", "date"], name="giftcardevent_user_date_idx"),
            BTreeIndex(fields=["type"], name="giftcardevent_type_idx"),
            BTreeIndex(fields=["order"], name="giftcardevent_order_idx"),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.gift_card.display_code} - {self.date}"

    @classmethod
    def log_event(cls, gift_card, event_type, user=None, **kwargs):
        """
        Log a gift card event.
        
        Args:
            gift_card: The gift card instance
            event_type: The event type from GiftCardEvents
            user: The user performing the action
            **kwargs: Additional parameters to store
        """
        return cls.objects.create(
            gift_card=gift_card,
            type=event_type,
            user=user,
            parameters=kwargs.get('parameters', {}),
            amount=kwargs.get('amount'),
            previous_balance=kwargs.get('previous_balance'),
            new_balance=kwargs.get('new_balance'),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent'),
            order=kwargs.get('order'),
        )



