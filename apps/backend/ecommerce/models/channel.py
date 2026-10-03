# apps/backend/ecommerce/models/channel.py
from datetime import timedelta

from django.conf import settings
from django.db import models
from django_countries.fields import CountryField

from core.models.metadata import ModelWithMetadata


# ============================================================================
# CHANNEL STRATEGY CONSTANTS
# ============================================================================

class AllocationStrategy:
    """Allocation strategy for channel."""
    
    PRIORITIZE_SORTING_ORDER = "prioritize-sorting-order"
    PRIORITIZE_HIGH_STOCK = "prioritize-high-stock"
    PRIORITIZE_LOW_STOCK = "prioritize-low-stock"
    
    CHOICES = [
        (PRIORITIZE_SORTING_ORDER, "Prioritize sorting order"),
        (PRIORITIZE_HIGH_STOCK, "Prioritize high stock"),
        (PRIORITIZE_LOW_STOCK, "Prioritize low stock"),
    ]


class MarkAsPaidStrategy:
    """Mark as paid strategy for channel."""
    
    PAYMENT_FLOW = "payment-flow"
    MANUAL = "manual"
    TRANSACTION_FLOW = "transaction-flow"
    
    CHOICES = [
        (PAYMENT_FLOW, "Payment flow"),
        (MANUAL, "Manual"),
        (TRANSACTION_FLOW, "Transaction flow"),
    ]


class TransactionFlowStrategy:
    """Transaction flow strategy for channel."""
    
    CHARGE = "charge"
    AUTHORIZE = "authorize"
    AUTHORIZE_AND_CAPTURE = "authorize-and-capture"
    
    CHOICES = [
        (CHARGE, "Charge"),
        (AUTHORIZE, "Authorize"),
        (AUTHORIZE_AND_CAPTURE, "Authorize and capture"),
    ]


# ============================================================================
# CHANNEL MODEL
# ============================================================================

class Channel(ModelWithMetadata):
    """
    Channel model for sales channels.
    
    Channels represent different sales channels like web store, mobile app,
    marketplaces, etc. Each channel can have its own configuration.
    """
    
    name = models.CharField(
        max_length=250,
        help_text="Display name of the channel"
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this channel is active"
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="Unique slug for the channel"
    )
    currency_code = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        help_text="Default currency for this channel"
    )
    default_country = CountryField(
        help_text="Default country for this channel"
    )

    allocation_strategy = models.CharField(
        max_length=255,
        choices=AllocationStrategy.CHOICES,
        default=AllocationStrategy.PRIORITIZE_SORTING_ORDER,
        help_text="Strategy for allocating stock"
    )

    order_mark_as_paid_strategy = models.CharField(
        max_length=255,
        choices=MarkAsPaidStrategy.CHOICES,
        default=MarkAsPaidStrategy.PAYMENT_FLOW,
        help_text="Strategy for marking orders as paid"
    )

    default_transaction_flow_strategy = models.CharField(
        max_length=255,
        choices=TransactionFlowStrategy.CHOICES,
        default=TransactionFlowStrategy.CHARGE,
        help_text="Default transaction flow strategy"
    )

    automatically_confirm_all_new_orders = models.BooleanField(
        default=True,
        null=True,
        help_text="Automatically confirm all new orders"
    )
    allow_unpaid_orders = models.BooleanField(
        default=False,
        help_text="Allow unpaid orders to be created"
    )
    automatically_fulfill_non_shippable_gift_card = models.BooleanField(
        default=True,
        null=True,
        help_text="Automatically fulfill non-shippable gift cards"
    )
    expire_orders_after = models.IntegerField(
        default=None,
        null=True,
        blank=True,
        help_text="Minutes until order expires."
    )

    delete_expired_orders_after = models.DurationField(
        default=timedelta(days=60),
        help_text="Duration after which expired orders are deleted.",
    )

    include_draft_order_in_voucher_usage = models.BooleanField(
        default=False,
        help_text="Include draft orders in voucher usage calculation"
    )
    use_legacy_error_flow_for_checkout = models.BooleanField(
        default=True,
        help_text="Use legacy error flow for checkout"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='channels_created',
        help_text="User who created this channel"
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='channels_modified',
        help_text="User who last modified this channel"
    )

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        
        permissions = (
            ("manage_channels", "Manage channels."),
        )
        indexes = [
            models.Index(fields=["slug"], name="channel_slug_idx"),
            models.Index(fields=["is_active"], name="channel_active_idx"),
            models.Index(fields=["default_country"], name="channel_country_idx"),
            models.Index(fields=["currency_code"], name="channel_currency_idx"),
        ]
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    def __str__(self):
        return f"{self.name} ({self.slug})"


    def get_default_currency(self):
        """Get the default currency for this channel."""
        return self.currency_code

    def get_default_country(self):
        """Get the default country for this channel."""
        return self.default_country

    def get_allocation_strategy_display(self):
        """Get display name for allocation strategy."""
        return dict(AllocationStrategy.CHOICES).get(self.allocation_strategy, self.allocation_strategy)

    def get_order_mark_as_paid_strategy_display(self):
        """Get display name for mark as paid strategy."""
        return dict(MarkAsPaidStrategy.CHOICES).get(self.order_mark_as_paid_strategy, self.order_mark_as_paid_strategy)

    def get_transaction_flow_strategy_display(self):
        """Get display name for transaction flow strategy."""
        return dict(TransactionFlowStrategy.CHOICES).get(self.default_transaction_flow_strategy, self.default_transaction_flow_strategy)

    @classmethod
    def get_default_channel(cls):
        """Get the default channel (first active channel)."""
        return cls.objects.filter(is_active=True).first()

    @classmethod
    def get_channel_by_slug(cls, slug):
        """Get a channel by its slug."""
        try:
            return cls.objects.get(slug=slug, is_active=True)
        except cls.DoesNotExist:
            return None


# ============================================================================
# CHANNEL HELPERS
# ============================================================================

def get_channel_from_request(request):
    """
    Get the current channel from the request.
    
    This can be implemented to get the channel from:
    - Request headers
    - Subdomain
    - URL parameter
    - Session
    - User preference
    
    Returns:
        Channel instance or None
    """
    # Example implementation - can be customized
    # Get from header
    channel_slug = request.headers.get('X-Channel-Slug')
    if channel_slug:
        return Channel.get_channel_by_slug(channel_slug)
    
    # Get from session
    channel_slug = request.session.get('channel_slug')
    if channel_slug:
        return Channel.get_channel_by_slug(channel_slug)
    
    # Get default
    return Channel.get_default_channel()


def get_channel_currency(channel):
    """
    Get the currency for a channel.
    
    Args:
        channel: Channel instance
    
    Returns:
        str: Currency code
    """
    if channel:
        return channel.currency_code
    return settings.DEFAULT_CURRENCY


def get_channel_country(channel):
    """
    Get the default country for a channel.
    
    Args:
        channel: Channel instance
    
    Returns:
        str: Country code
    """
    if channel:
        return str(channel.default_country)
    return settings.DEFAULT_COUNTRY_CODE if hasattr(settings, 'DEFAULT_COUNTRY_CODE') else 'US'

