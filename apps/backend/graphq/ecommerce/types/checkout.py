# graphql/ecommerce/types/checkout.py

"""
GraphQL Nodes for Checkout, CheckoutLine, and CheckoutMetadata.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.checkout import Checkout, CheckoutLine, CheckoutMetadata



class CheckoutLineNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Checkout Line.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    total_price_display = String(description="Formatted total price")
    unit_price = Decimal(description="Unit price of the item")
    unit_price_display = String(description="Formatted unit price")
    is_shipping_required = Boolean(description="Whether item requires shipping")
    line_total = Decimal(description="Total price for this line (quantity * unit price)")
    line_total_display = String(description="Formatted line total")
    tax_rate_display = String(description="Formatted tax rate as percentage")
    
     
    class Meta:
        model = CheckoutLine
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'checkout': ['exact'],
            'variant': ['exact'],
            'created_by': ['exact'],
            'modified_by': ['exact'],
            
            # Numeric fields
            'quantity': ['exact', 'gte', 'lte'],
            'price_override': ['exact', 'gte', 'lte', 'isnull'],
            'total_price_net_amount': ['exact', 'gte', 'lte'],
            'total_price_gross_amount': ['exact', 'gte', 'lte'],
            'tax_rate': ['exact', 'gte', 'lte'],
            'currency': ['exact'],
            
            # Boolean fields
            'is_gift': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Calculated Properties
    # ============================================================
    
    def resolve_total_price_display(self, info):
        """Resolve formatted total price."""
        if self.total_price_gross_amount:
            return f"${self.total_price_gross_amount:,.2f}"
        return None
    
    def resolve_unit_price(self, info):
        """Resolve unit price of the item."""
        if self.price_override:
            return float(self.price_override)
        if self.variant and self.variant.price:
            return float(self.variant.price)
        return 0
    
    def resolve_unit_price_display(self, info):
        """Resolve formatted unit price."""
        unit_price = self.resolve_unit_price(info)
        return f"${unit_price:,.2f}" if unit_price else None
    
    def resolve_is_shipping_required(self, info):
        """Resolve whether item requires shipping."""
        return self.is_shipping_required()
    
    def resolve_line_total(self, info):
        """Resolve total price for this line (quantity * unit price)."""
        return self.resolve_unit_price(info) * self.quantity
    
    def resolve_line_total_display(self, info):
        """Resolve formatted line total."""
        line_total = self.resolve_line_total(info)
        return f"${line_total:,.2f}" if line_total else None
    
    def resolve_tax_rate_display(self, info):
        """Resolve formatted tax rate as percentage."""
        if self.tax_rate:
            return f"{self.tax_rate * 100:.1f}%"
        return "0.0%"
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_checkout_details(self, info):
        """Resolve parent checkout."""
        return self.checkout
    
    def resolve_variant_details(self, info):
        """Resolve product variant."""
        return self.variant
    
    def resolve_created_by_details(self, info):
        """Resolve user who created this line."""
        return self.created_by
    
    def resolve_modified_by_details(self, info):
        """Resolve user who last modified this line."""
        return self.modified_by


class CheckoutNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Checkout with full checkout management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_locked = Boolean(description="Whether checkout is locked")
    is_shipping_required = Boolean(description="Whether shipping is required")
    is_tax_exempt = Boolean(description="Whether checkout is tax exempt")
    has_tax_error = Boolean(description="Whether there is a tax error")
    has_billing_address = Boolean(description="Whether billing address is set")
    has_shipping_address = Boolean(description="Whether shipping address is set")
    has_shipping_method = Boolean(description="Whether shipping method is set")
    has_gift_cards = Boolean(description="Whether gift cards are applied")
    has_voucher = Boolean(description="Whether voucher is applied")
    is_completable = Boolean(description="Whether checkout can be completed")
    
    # Display fields
    customer_email = String(description="Customer email address")
    authorize_status_display = String(description="Human-readable authorize status")
    charge_status_display = String(description="Human-readable charge status")
    total_display = String(description="Formatted total amount")
    subtotal_display = String(description="Formatted subtotal amount")
    shipping_price_display = String(description="Formatted shipping price")
    discount_display = String(description="Formatted discount amount")
    base_total_display = String(description="Formatted base total")
    base_subtotal_display = String(description="Formatted base subtotal")
    
    # Amount fields
    total_gift_cards_balance = Decimal(description="Total balance of applied gift cards")
    total_gift_cards_balance_display = String(description="Formatted total gift cards balance")
    line_count = Int(description="Number of lines in checkout")
    total_quantity = Int(description="Total quantity of items")
    
    
    class Meta:
        model = Checkout
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = { 
            # Foreign keys
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            'channel': ['exact'],
            'channel__slug': ['exact'],
            'billing_address': ['exact'],
            'shipping_address': ['exact'],
            'shipping_method': ['exact'],
            'collection_point': ['exact'],
            
            # String fields
            'email': ['exact', 'icontains'],
            'token': ['exact'],
            'currency': ['exact'],
            'country': ['exact'],
            'voucher_code': ['exact', 'icontains'],
            'discount_name': ['exact', 'icontains'],
            'translated_discount_name': ['exact', 'icontains'],
            'redirect_url': ['exact', 'icontains'],
            'tracking_code': ['exact', 'icontains'],
            'language_code': ['exact'],
            'note': ['exact', 'icontains'],
            'tax_error': ['exact', 'icontains'],
            
            # Boolean fields
            'automatically_refundable': ['exact'],
            'tax_exemption': ['exact'],
            'is_voucher_usage_increased': ['exact'],
            
            # Numeric fields
            'total_net_amount': ['exact', 'gte', 'lte'],
            'total_gross_amount': ['exact', 'gte', 'lte'],
            'base_total_amount': ['exact', 'gte', 'lte'],
            'subtotal_net_amount': ['exact', 'gte', 'lte'],
            'subtotal_gross_amount': ['exact', 'gte', 'lte'],
            'base_subtotal_amount': ['exact', 'gte', 'lte'],
            'shipping_price_net_amount': ['exact', 'gte', 'lte'],
            'shipping_price_gross_amount': ['exact', 'gte', 'lte'],
            'shipping_tax_rate': ['exact', 'gte', 'lte'],
            'discount_amount': ['exact', 'gte', 'lte'],
            
            # Choice fields
            'authorize_status': ['exact'],
            'charge_status': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'last_change': ['exact', 'gte', 'lte'],
            'completing_started_at': ['exact', 'gte', 'lte', 'isnull'],
            'last_transaction_modified_at': ['exact', 'gte', 'lte', 'isnull'],
            'price_expiration': ['exact', 'gte', 'lte'],
        }
        
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_locked(self, info):
        """Resolve whether checkout is locked."""
        return self.is_checkout_locked()
    
    def resolve_is_shipping_required(self, info):
        """Resolve whether shipping is required."""
        return self.is_shipping_required()
    
    def resolve_is_tax_exempt(self, info):
        """Resolve whether checkout is tax exempt."""
        return self.tax_exemption
    
    def resolve_has_tax_error(self, info):
        """Resolve whether there is a tax error."""
        return bool(self.tax_error)
    
    def resolve_has_billing_address(self, info):
        """Resolve whether billing address is set."""
        return self.billing_address is not None
    
    def resolve_has_shipping_address(self, info):
        """Resolve whether shipping address is set."""
        return self.shipping_address is not None
    
    def resolve_has_shipping_method(self, info):
        """Resolve whether shipping method is set."""
        return self.shipping_method is not None
    
    def resolve_has_gift_cards(self, info):
        """Resolve whether gift cards are applied."""
        return self.gift_cards.exists() if hasattr(self, 'gift_cards') else False
    
    def resolve_has_voucher(self, info):
        """Resolve whether voucher is applied."""
        return bool(self.voucher_code)
    
    def resolve_is_completable(self, info):
        """Resolve whether checkout can be completed."""
        return all([
            self.has_billing_address,
            self.is_shipping_required() == self.has_shipping_address,
            self.is_shipping_required() == self.has_shipping_method,
            self.lines.exists(),
            not self.is_locked,
        ])
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_customer_email(self, info):
        """Resolve customer email address."""
        return self.get_customer_email()
    
    def resolve_authorize_status_display(self, info):
        """Resolve human-readable authorize status."""
        return dict(Checkout.AUTHORIZE_STATUS_CHOICES).get(self.authorize_status, self.authorize_status)
    
    def resolve_charge_status_display(self, info):
        """Resolve human-readable charge status."""
        return dict(Checkout.CHARGE_STATUS_CHOICES).get(self.charge_status, self.charge_status)
    
    def resolve_total_display(self, info):
        """Resolve formatted total amount."""
        if self.total_gross_amount:
            return f"${self.total_gross_amount:,.2f}"
        return None
    
    def resolve_subtotal_display(self, info):
        """Resolve formatted subtotal amount."""
        if self.subtotal_gross_amount:
            return f"${self.subtotal_gross_amount:,.2f}"
        return None
    
    def resolve_shipping_price_display(self, info):
        """Resolve formatted shipping price."""
        if self.shipping_price_gross_amount:
            return f"${self.shipping_price_gross_amount:,.2f}"
        return None
    
    def resolve_discount_display(self, info):
        """Resolve formatted discount amount."""
        if self.discount_amount:
            return f"${self.discount_amount:,.2f}"
        return None
    
    def resolve_base_total_display(self, info):
        """Resolve formatted base total."""
        if self.base_total_amount:
            return f"${self.base_total_amount:,.2f}"
        return None
    
    def resolve_base_subtotal_display(self, info):
        """Resolve formatted base subtotal."""
        if self.base_subtotal_amount:
            return f"${self.base_subtotal_amount:,.2f}"
        return None
    
    # ============================================================
    # Resolvers - Amount Fields
    # ============================================================
    
    def resolve_total_gift_cards_balance(self, info):
        """Resolve total balance of applied gift cards."""
        if hasattr(self, 'get_total_gift_cards_balance'):
            balance = self.get_total_gift_cards_balance()
            if balance:
                return float(balance.amount)
        return 0
    
    def resolve_total_gift_cards_balance_display(self, info):
        """Resolve formatted total gift cards balance."""
        balance = self.resolve_total_gift_cards_balance(info)
        return f"${balance:,.2f}" if balance else None
    
    def resolve_line_count(self, info):
        """Resolve number of lines in checkout."""
        return self.lines.count()
    
    def resolve_total_quantity(self, info):
        """Resolve total quantity of items."""
        return self.lines.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_user_details(self, info):
        """Resolve user who owns this checkout."""
        return self.user
    
    def resolve_channel_details(self, info):
        """Resolve channel for this checkout."""
        return self.channel
    
    def resolve_billing_address_details(self, info):
        """Resolve billing address."""
        return self.billing_address
    
    def resolve_shipping_address_details(self, info):
        """Resolve shipping address."""
        return self.shipping_address
    
    def resolve_shipping_method_details(self, info):
        """Resolve shipping method."""
        return self.shipping_method
    
    def resolve_collection_point_details(self, info):
        """Resolve collection point."""
        return self.collection_point
    
    def resolve_lines(self, info):
        """Resolve checkout lines."""
        return self.lines.all().order_by('created_at')
    
    def resolve_payments(self, info):
        """Resolve payments for this checkout."""
        return self.payments.all() if hasattr(self, 'payments') else []
    
    def resolve_gift_cards(self, info):
        """Resolve applied gift cards."""
        return self.gift_cards.all() if hasattr(self, 'gift_cards') else []
    
    def resolve_metadata_storage(self, info):
        """Resolve metadata storage."""
        return getattr(self, 'metadata_storage', None)


class CheckoutMetadataNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Checkout Metadata.
    """
    
    class Meta:
        model = CheckoutMetadata
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'id': ['exact'],
            'checkout': ['exact'],
        }
        ordering = ['id']
    
    def resolve_checkout_details(self, info):
        """Resolve parent checkout."""
        return self.checkout

