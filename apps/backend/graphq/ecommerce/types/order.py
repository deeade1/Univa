# graphql/ecommerce/types/order.py

"""
GraphQL Nodes for Order, OrderLine, Fulfillment, FulfillmentLine, and OrderEvent.
"""

from graphene import Node, String, Boolean, Field, List, DateTime, Int, Decimal, UUID, JSONString, Float
from graphene_django_optimizer import OptimizedDjangoObjectType

from ecommerce.models.order import (
    Order,
    OrderLine,
    Fulfillment,
    FulfillmentLine,
    OrderEvent,
    OrderGrantedRefund,
    OrderGrantedRefundLine,
    OrderPerformanceMetrics,
    OrderSplit,
    OrderMerge,
    OrderTrackingEvent,
    OrderFraudAssessment,
    OrderPromise,
)



class FulfillmentLineNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Fulfillment Line.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    display_name = String(description="Display name for the fulfillment line")
    
    
    class Meta:
        model = FulfillmentLine
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'order_line': ['exact'],
            'fulfillment': ['exact'],
            'stock': ['exact'],
            'quantity': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_display_name(self, info):
        """Resolve display name for the fulfillment line."""
        if self.order_line:
            return f"{self.order_line.product_name} x {self.quantity}"
        return f"Fulfillment Line #{self.id}"
    
    def resolve_order_line_details(self, info):
        """Resolve order line details."""
        return self.order_line
    
    def resolve_fulfillment_details(self, info):
        """Resolve fulfillment details."""
        return self.fulfillment
    
    def resolve_stock_details(self, info):
        """Resolve stock details."""
        return self.stock


class FulfillmentNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Fulfillment with full fulfillment management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    composed_id = String(description="Composed ID (order number - fulfillment order)")
    status_display = String(description="Human-readable status display")
    total_quantity = Int(description="Total quantity across fulfillment lines")
    is_tracking_number_url = Boolean(description="Whether tracking number is a URL")
    can_edit = Boolean(description="Whether fulfillment can be edited")
    line_count = Int(description="Number of lines in this fulfillment")
    is_completed = Boolean(description="Whether fulfillment is completed")
    is_cancelled = Boolean(description="Whether fulfillment is cancelled")
    is_refunded = Boolean(description="Whether fulfillment is refunded")
    
    class Meta:
        model = Fulfillment
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            
            # String fields
            'status': ['exact'],
            'tracking_number': ['exact', 'icontains'],
            
            # Numeric fields
            'fulfillment_order': ['exact', 'gte', 'lte'],
            'shipping_refund_amount': ['exact', 'gte', 'lte', 'isnull'],
            'total_refund_amount': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_composed_id(self, info):
        """Resolve composed ID (order number - fulfillment order)."""
        return self.composed_id
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(FulfillmentStatus.CHOICES).get(self.status, self.status)
    
    def resolve_total_quantity(self, info):
        """Resolve total quantity across fulfillment lines."""
        return self.get_total_quantity()
    
    def resolve_is_tracking_number_url(self, info):
        """Resolve whether tracking number is a URL."""
        return self.is_tracking_number_url
    
    def resolve_can_edit(self, info):
        """Resolve whether fulfillment can be edited."""
        return self.can_edit()
    
    def resolve_line_count(self, info):
        """Resolve number of lines in this fulfillment."""
        return self.lines.count()
    
    def resolve_is_completed(self, info):
        """Resolve whether fulfillment is completed."""
        return self.status == FulfillmentStatus.FULFILLED
    
    def resolve_is_cancelled(self, info):
        """Resolve whether fulfillment is cancelled."""
        return self.status == FulfillmentStatus.CANCELED
    
    def resolve_is_refunded(self, info):
        """Resolve whether fulfillment is refunded."""
        return self.status == FulfillmentStatus.REFUNDED
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_lines(self, info):
        """Resolve fulfillment lines."""
        return self.lines.all()
    
    def resolve_tracking_url(self, info):
        """Resolve tracking URL if tracking number is a URL."""
        if self.is_tracking_number_url:
            return self.tracking_number
        return None


class OrderEventNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Event.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    type_display = String(description="Human-readable type display")
    event_summary = String(description="Summary of the event")
    user_display = String(description="User display name")
    

    class Meta:
        model = OrderEvent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            'user': ['exact'],
            'related': ['exact'],
            
            # String fields
            'type': ['exact'],
            
            # Date fields
            'date': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_type_display(self, info):
        """Resolve human-readable type display."""
        return dict(OrderEvents.CHOICES).get(self.type, self.type)
    
    def resolve_event_summary(self, info):
        """Resolve summary of the event."""
        if self.type == OrderEvents.ORDER_CREATED:
            return f"Order #{self.order.number} was created"
        elif self.type == OrderEvents.ORDER_CONFIRMED:
            return f"Order #{self.order.number} was confirmed"
        elif self.type == OrderEvents.ORDER_CANCELLED:
            return f"Order #{self.order.number} was cancelled"
        elif self.type == OrderEvents.ORDER_FULFILLED:
            return f"Order #{self.order.number} was fulfilled"
        elif self.type == OrderEvents.ORDER_PAID:
            return f"Order #{self.order.number} was paid"
        elif self.type == OrderEvents.ORDER_REFUNDED:
            return f"Order #{self.order.number} was refunded"
        return f"Event on order #{self.order.number}"
    
    def resolve_user_display(self, info):
        """Resolve user display name."""
        if self.user:
            return self.user.get_full_name() or self.user.email
        return "System"
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_user_details(self, info):
        """Resolve user who triggered the event."""
        return self.user
    
    def resolve_related_event_details(self, info):
        """Resolve related event."""
        return self.related


class OrderLineNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Line with full line management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    quantity_unfulfilled = Int(description="Unfulfilled quantity")
    is_digital = Boolean(description="Whether the product is digital")
    display_name = String(description="Display name of the line")
    unit_price_display = String(description="Formatted unit price")
    total_price_display = String(description="Formatted total price")
    undiscounted_total_price_display = String(description="Formatted undiscounted total price")
    unit_discount_display = String(description="Formatted unit discount")
    unit_discount_type_display = String(description="Human-readable discount type display")
    tax_rate_display = String(description="Formatted tax rate as percentage")
    

    class Meta:
        model = OrderLine
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            'variant': ['exact'],
            'allocated_warehouse': ['exact'],
            'tax_class': ['exact'],
            
            # String fields
            'product_name': ['exact', 'icontains'],
            'variant_name': ['exact', 'icontains'],
            'translated_product_name': ['exact', 'icontains'],
            'translated_variant_name': ['exact', 'icontains'],
            'product_sku': ['exact', 'icontains'],
            'product_variant_id': ['exact', 'icontains'],
            'currency': ['exact'],
            'voucher_code': ['exact', 'icontains'],
            'sale_id': ['exact', 'icontains'],
            'unit_discount_reason': ['exact', 'icontains'],
            'bin_location': ['exact', 'icontains'],
            'return_reason': ['exact', 'icontains'],
            'return_condition': ['exact', 'icontains'],
            'defect_type': ['exact', 'icontains'],
            'unit_discount_type': ['exact'],
            
            # Numeric fields
            'quantity': ['exact', 'gte', 'lte'],
            'quantity_fulfilled': ['exact', 'gte', 'lte'],
            'unit_price_net_amount': ['exact', 'gte', 'lte'],
            'unit_price_gross_amount': ['exact', 'gte', 'lte'],
            'total_price_net_amount': ['exact', 'gte', 'lte'],
            'total_price_gross_amount': ['exact', 'gte', 'lte'],
            'tax_rate': ['exact', 'gte', 'lte', 'isnull'],
            'unit_discount_amount': ['exact', 'gte', 'lte'],
            'unit_discount_value': ['exact', 'gte', 'lte'],
            'unit_cost': ['exact', 'gte', 'lte', 'isnull'],
            'landed_cost': ['exact', 'gte', 'lte', 'isnull'],
            'pick_path_sequence': ['exact', 'gte', 'lte', 'isnull'],
            'line_rating': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'is_shipping_required': ['exact'],
            'is_gift_card': ['exact'],
            'is_gift': ['exact'],
            'is_price_overridden': ['exact'],
            'is_defective': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_quantity_unfulfilled(self, info):
        """Resolve unfulfilled quantity."""
        return self.quantity_unfulfilled
    
    def resolve_is_digital(self, info):
        """Resolve whether the product is digital."""
        return self.is_digital
    
    def resolve_display_name(self, info):
        """Resolve display name of the line."""
        if self.variant_name:
            return f"{self.product_name} ({self.variant_name})"
        return self.product_name
    
    def resolve_unit_price_display(self, info):
        """Resolve formatted unit price."""
        if self.unit_price_gross_amount:
            return f"{self.unit_price_gross_amount:.2f} {self.currency}"
        return None
    
    def resolve_total_price_display(self, info):
        """Resolve formatted total price."""
        if self.total_price_gross_amount:
            return f"{self.total_price_gross_amount:.2f} {self.currency}"
        return None
    
    def resolve_undiscounted_total_price_display(self, info):
        """Resolve formatted undiscounted total price."""
        if self.undiscounted_total_price_gross_amount:
            return f"{self.undiscounted_total_price_gross_amount:.2f} {self.currency}"
        return None
    
    def resolve_unit_discount_display(self, info):
        """Resolve formatted unit discount."""
        if self.unit_discount_amount:
            return f"{self.unit_discount_amount:.2f} {self.currency}"
        return None
    
    def resolve_unit_discount_type_display(self, info):
        """Resolve human-readable discount type display."""
        if self.unit_discount_type:
            return dict(DiscountValueType.CHOICES).get(self.unit_discount_type, self.unit_discount_type)
        return None
    
    def resolve_tax_rate_display(self, info):
        """Resolve formatted tax rate as percentage."""
        if self.tax_rate:
            return f"{float(self.tax_rate) * 100:.1f}%"
        return None
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_variant_details(self, info):
        """Resolve product variant details."""
        return self.variant
    
    def resolve_fulfillment_lines(self, info):
        """Resolve fulfillment lines."""
        return self.fulfillment_lines.all()
    
    def resolve_discounts(self, info):
        """Resolve line discounts."""
        return self.discounts.all()
    
    def resolve_allocated_warehouse_details(self, info):
        """Resolve allocated warehouse details."""
        return self.allocated_warehouse


class OrderNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order with full order management.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    # Status checks
    is_fully_paid = Boolean(description="Whether order is fully paid")
    is_partly_paid = Boolean(description="Whether order has received any payment")
    is_draft = Boolean(description="Whether order is a draft")
    is_unconfirmed = Boolean(description="Whether order is unconfirmed")
    is_expired = Boolean(description="Whether order is expired")
    is_open = Boolean(description="Whether order is open")
    is_shipping_required = Boolean(description="Whether any line requires shipping")
    is_pre_authorized = Boolean(description="Whether order has a successful authorization")
    is_captured = Boolean(description="Whether order has a successful capture")
    can_cancel = Boolean(description="Whether order can be cancelled")
    can_capture = Boolean(description="Whether order can be captured")
    can_void = Boolean(description="Whether order can be voided")
    can_refund = Boolean(description="Whether order can be refunded")
    can_mark_as_paid = Boolean(description="Whether order can be manually marked as paid")
    
    # Display fields
    status_display = String(description="Human-readable status display")
    authorize_status_display = String(description="Human-readable authorize status display")
    charge_status_display = String(description="Human-readable charge status display")
    origin_display = String(description="Human-readable origin display")
    customer_email = String(description="Customer email address")
    total_balance = Decimal(description="Current payment balance")
    total_display = String(description="Formatted total amount")
    subtotal_display = String(description="Formatted subtotal amount")
    shipping_price_display = String(description="Formatted shipping price")
    total_charged_display = String(description="Formatted total charged amount")
    total_authorized_display = String(description="Formatted total authorized amount")
    
    # Counts
    line_count = Int(description="Number of lines in the order")
    total_quantity = Int(description="Total quantity across all lines")
    fulfillment_count = Int(description="Number of fulfillments")
    event_count = Int(description="Number of events")
    

    
    class Meta:
        model = Order
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'user': ['exact'],
            'user__email': ['exact', 'icontains'],
            'channel': ['exact'],
            'channel__slug': ['exact'],
            'shipping_method': ['exact'],
            'billing_address': ['exact'],
            'shipping_address': ['exact'],
            'collection_point': ['exact'],
            'preferred_warehouse': ['exact'],
            'voucher': ['exact'],
            'original': ['exact'],
            
            # String fields
            'number': ['exact'],
            'status': ['exact'],
            'authorize_status': ['exact'],
            'charge_status': ['exact'],
            'origin': ['exact'],
            'user_email': ['exact', 'icontains'],
            'language_code': ['exact'],
            'currency': ['exact'],
            'shipping_method_name': ['exact', 'icontains'],
            'collection_point_name': ['exact', 'icontains'],
            'checkout_token': ['exact', 'icontains'],
            'voucher_code': ['exact', 'icontains'],
            'customer_note': ['exact', 'icontains'],
            'acquisition_channel': ['exact', 'icontains'],
            'campaign_id': ['exact', 'icontains'],
            'attribution_model': ['exact', 'icontains'],
            'review_id': ['exact', 'icontains'],
            
            # Numeric fields
            'total_net_amount': ['exact', 'gte', 'lte'],
            'total_gross_amount': ['exact', 'gte', 'lte'],
            'shipping_price_net_amount': ['exact', 'gte', 'lte'],
            'shipping_price_gross_amount': ['exact', 'gte', 'lte'],
            'total_charged_amount': ['exact', 'gte', 'lte'],
            'total_authorized_amount': ['exact', 'gte', 'lte'],
            'priority_level': ['exact', 'gte', 'lte'],
            'fraud_score': ['exact', 'gte', 'lte', 'isnull'],
            'customer_satisfaction_score': ['exact', 'gte', 'lte', 'isnull'],
            'net_promoter_score': ['exact', 'gte', 'lte', 'isnull'],
            'carbon_footprint_kg': ['exact', 'gte', 'lte', 'isnull'],
            'gross_margin': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'display_gross_prices': ['exact'],
            'tax_exemption': ['exact'],
            'should_refresh_prices': ['exact'],
            'is_prime': ['exact'],
            'is_business': ['exact'],
            'is_express': ['exact'],
            'is_carbon_neutral': ['exact'],
            'requires_manual_review': ['exact'],
            'reviewed_by_fraud_team': ['exact'],
            'would_repurchase': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
            'expired_at': ['exact', 'gte', 'lte', 'isnull'],
            'promised_delivery_date': ['exact', 'gte', 'lte', 'isnull'],
            'actual_delivery_date': ['exact', 'gte', 'lte', 'isnull'],
            'delivery_window_start': ['exact', 'gte', 'lte', 'isnull'],
            'delivery_window_end': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    # ============================================================
    # Resolvers - Status Checks
    # ============================================================
    
    def resolve_is_fully_paid(self, info):
        """Resolve whether order is fully paid."""
        return self.is_fully_paid()
    
    def resolve_is_partly_paid(self, info):
        """Resolve whether order has received any payment."""
        return self.is_partly_paid()
    
    def resolve_is_draft(self, info):
        """Resolve whether order is a draft."""
        return self.is_draft()
    
    def resolve_is_unconfirmed(self, info):
        """Resolve whether order is unconfirmed."""
        return self.is_unconfirmed()
    
    def resolve_is_expired(self, info):
        """Resolve whether order is expired."""
        return self.is_expired()
    
    def resolve_is_open(self, info):
        """Resolve whether order is open."""
        return self.is_open()
    
    def resolve_is_shipping_required(self, info):
        """Resolve whether any line requires shipping."""
        return self.is_shipping_required()
    
    def resolve_is_pre_authorized(self, info):
        """Resolve whether order has a successful authorization."""
        return self.is_pre_authorized()
    
    def resolve_is_captured(self, info):
        """Resolve whether order has a successful capture."""
        return self.is_captured()
    
    def resolve_can_cancel(self, info):
        """Resolve whether order can be cancelled."""
        return self.can_cancel()
    
    def resolve_can_capture(self, info):
        """Resolve whether order can be captured."""
        return self.can_capture()
    
    def resolve_can_void(self, info):
        """Resolve whether order can be voided."""
        return self.can_void()
    
    def resolve_can_refund(self, info):
        """Resolve whether order can be refunded."""
        return self.can_refund()
    
    def resolve_can_mark_as_paid(self, info):
        """Resolve whether order can be manually marked as paid."""
        return self.can_mark_as_paid()
    
    # ============================================================
    # Resolvers - Display Fields
    # ============================================================
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(OrderStatus.CHOICES).get(self.status, self.status)
    
    def resolve_authorize_status_display(self, info):
        """Resolve human-readable authorize status display."""
        return dict(OrderAuthorizeStatus.CHOICES).get(self.authorize_status, self.authorize_status)
    
    def resolve_charge_status_display(self, info):
        """Resolve human-readable charge status display."""
        return dict(OrderChargeStatus.CHOICES).get(self.charge_status, self.charge_status)
    
    def resolve_origin_display(self, info):
        """Resolve human-readable origin display."""
        return dict(OrderOrigin.CHOICES).get(self.origin, self.origin)
    
    def resolve_customer_email(self, info):
        """Resolve customer email address."""
        return self.get_customer_email()
    
    def resolve_total_balance(self, info):
        """Resolve current payment balance."""
        return float(self.total_balance.amount) if self.total_balance else None
    
    def resolve_total_display(self, info):
        """Resolve formatted total amount."""
        if self.total_gross_amount:
            return f"{self.total_gross_amount:.2f} {self.currency}"
        return None
    
    def resolve_subtotal_display(self, info):
        """Resolve formatted subtotal amount."""
        if self.subtotal_gross_amount:
            return f"{self.subtotal_gross_amount:.2f} {self.currency}"
        return None
    
    def resolve_shipping_price_display(self, info):
        """Resolve formatted shipping price."""
        if self.shipping_price_gross_amount:
            return f"{self.shipping_price_gross_amount:.2f} {self.currency}"
        return None
    
    def resolve_total_charged_display(self, info):
        """Resolve formatted total charged amount."""
        if self.total_charged_amount:
            return f"{self.total_charged_amount:.2f} {self.currency}"
        return None
    
    def resolve_total_authorized_display(self, info):
        """Resolve formatted total authorized amount."""
        if self.total_authorized_amount:
            return f"{self.total_authorized_amount:.2f} {self.currency}"
        return None
    
    # ============================================================
    # Resolvers - Counts
    # ============================================================
    
    def resolve_line_count(self, info):
        """Resolve number of lines in the order."""
        return self.lines.count()
    
    def resolve_total_quantity(self, info):
        """Resolve total quantity across all lines."""
        return self.get_total_quantity()
    
    def resolve_fulfillment_count(self, info):
        """Resolve number of fulfillments."""
        return self.fulfillments.count()
    
    def resolve_event_count(self, info):
        """Resolve number of events."""
        return self.events.count()
    
    # ============================================================
    # Resolvers - Nested Fields
    # ============================================================
    
    def resolve_user_details(self, info):
        """Resolve user who placed the order."""
        return self.user
    
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
    
    def resolve_preferred_warehouse_details(self, info):
        """Resolve preferred warehouse."""
        return self.preferred_warehouse
    
    def resolve_channel_details(self, info):
        """Resolve channel."""
        return self.channel
    
    def resolve_original_order_details(self, info):
        """Resolve original order."""
        return self.original
    
    def resolve_lines(self, info):
        """Resolve order lines."""
        return self.lines.all().order_by('created_at')
    
    def resolve_fulfillments(self, info):
        """Resolve fulfillments."""
        return self.fulfillments.all().order_by('created_at')
    
    def resolve_payments(self, info):
        """Resolve payments."""
        return self.payments.all()
    
    def resolve_events(self, info):
        """Resolve order events."""
        return self.events.all().order_by('date')
    
    def resolve_discounts(self, info):
        """Resolve order discounts."""
        return self.discounts.all()
    
    def resolve_gift_cards(self, info):
        """Resolve gift cards used."""
        return self.gift_cards.all()
    
    def resolve_voucher_details(self, info):
        """Resolve voucher used."""
        return self.voucher


class OrderGrantedRefundLineNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Granted Refund Line.
    """
    class Meta:
        model = OrderGrantedRefundLine
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            'order_line': ['exact'],
            'granted_refund': ['exact'],
            'quantity': ['exact', 'gte', 'lte'],
            'reason': ['exact', 'icontains'],
        }
        
    
    def resolve_order_line_details(self, info):
        """Resolve order line details."""
        return self.order_line
    
    def resolve_granted_refund_details(self, info):
        """Resolve granted refund details."""
        return self.granted_refund


class OrderGrantedRefundNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Granted Refund.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    status_display = String(description="Human-readable status display")
    amount_display = String(description="Formatted amount")
    is_completed = Boolean(description="Whether refund is completed")
    is_pending = Boolean(description="Whether refund is pending")
    is_failed = Boolean(description="Whether refund failed")
    line_count = Int(description="Number of refund lines")
    
    class Meta:
        model = OrderGrantedRefund
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            'user': ['exact'],
            'transaction_item': ['exact'],
            
            # String fields
            'status': ['exact'],
            'currency': ['exact'],
            'reason': ['exact', 'icontains'],
            
            # Numeric fields
            'amount_value': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'shipping_costs_included': ['exact'],
            
            # Date fields
            'created_at': ['exact', 'gte', 'lte'],
            'updated_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_status_display(self, info):
        """Resolve human-readable status display."""
        return dict(OrderGrantedRefundStatus.CHOICES).get(self.status, self.status)
    
    def resolve_amount_display(self, info):
        """Resolve formatted amount."""
        if self.amount_value:
            return f"{self.amount_value:.2f} {self.currency}"
        return None
    
    def resolve_is_completed(self, info):
        """Resolve whether refund is completed."""
        return self.status == OrderGrantedRefundStatus.COMPLETED
    
    def resolve_is_pending(self, info):
        """Resolve whether refund is pending."""
        return self.status == OrderGrantedRefundStatus.PENDING
    
    def resolve_is_failed(self, info):
        """Resolve whether refund failed."""
        return self.status == OrderGrantedRefundStatus.FAILED
    
    def resolve_line_count(self, info):
        """Resolve number of refund lines."""
        return self.lines.count()
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_user_details(self, info):
        """Resolve user who created the refund."""
        return self.user
    
    def resolve_transaction_item_details(self, info):
        """Resolve transaction item details."""
        return self.transaction_item
    
    def resolve_lines(self, info):
        """Resolve refund lines."""
        return self.lines.all()


class OrderPerformanceMetricsNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Performance Metrics.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    customer_lifetime_value_display = String(description="Formatted customer lifetime value")
    customer_acquisition_cost_display = String(description="Formatted customer acquisition cost")
    fulfillment_cost_display = String(description="Formatted fulfillment cost")
    shipping_cost_display = String(description="Formatted shipping cost")
    packaging_cost_display = String(description="Formatted packaging cost")
    gross_margin_display = String(description="Formatted gross margin")
    contribution_margin_display = String(description="Formatted contribution margin")
    

    class Meta:
        model = OrderPerformanceMetrics
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            
            # Numeric fields
            'customer_lifetime_value': ['exact', 'gte', 'lte'],
            'customer_acquisition_cost': ['exact', 'gte', 'lte'],
            'customer_retention_score': ['exact', 'gte', 'lte'],
            'days_to_fulfill': ['exact', 'gte', 'lte'],
            'days_to_deliver': ['exact', 'gte', 'lte'],
            'same_day_fulfillment_rate': ['exact', 'gte', 'lte'],
            'two_day_fulfillment_rate': ['exact', 'gte', 'lte'],
            'gross_margin': ['exact', 'gte', 'lte'],
            'contribution_margin': ['exact', 'gte', 'lte'],
            'fulfillment_cost': ['exact', 'gte', 'lte'],
            'shipping_cost': ['exact', 'gte', 'lte'],
            'packaging_cost': ['exact', 'gte', 'lte'],
            'perfect_order_score': ['exact', 'gte', 'lte'],
            'defect_rate': ['exact', 'gte', 'lte'],
            'return_rate': ['exact', 'gte', 'lte'],
            'net_promoter_score': ['exact', 'gte', 'lte', 'isnull'],
            'customer_satisfaction_score': ['exact', 'gte', 'lte', 'isnull'],
            'review_score': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'calculated_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_customer_lifetime_value_display(self, info):
        """Resolve formatted customer lifetime value."""
        if self.customer_lifetime_value:
            return f"${self.customer_lifetime_value:,.2f}"
        return None
    
    def resolve_customer_acquisition_cost_display(self, info):
        """Resolve formatted customer acquisition cost."""
        if self.customer_acquisition_cost:
            return f"${self.customer_acquisition_cost:,.2f}"
        return None
    
    def resolve_fulfillment_cost_display(self, info):
        """Resolve formatted fulfillment cost."""
        if self.fulfillment_cost:
            return f"${self.fulfillment_cost:,.2f}"
        return None
    
    def resolve_shipping_cost_display(self, info):
        """Resolve formatted shipping cost."""
        if self.shipping_cost:
            return f"${self.shipping_cost:,.2f}"
        return None
    
    def resolve_packaging_cost_display(self, info):
        """Resolve formatted packaging cost."""
        if self.packaging_cost:
            return f"${self.packaging_cost:,.2f}"
        return None
    
    def resolve_gross_margin_display(self, info):
        """Resolve formatted gross margin."""
        if self.gross_margin:
            return f"{float(self.gross_margin) * 100:.1f}%"
        return None
    
    def resolve_contribution_margin_display(self, info):
        """Resolve formatted contribution margin."""
        if self.contribution_margin:
            return f"{float(self.contribution_margin) * 100:.1f}%"
        return None
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order


class OrderSplitNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Split.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    split_type_display = String(description="Human-readable split type display")
    
    class Meta:
        model = OrderSplit
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'parent_order': ['exact'],
            'child_order': ['exact'],
            'split_by': ['exact'],
            
            # String fields
            'split_type': ['exact'],
            'reason': ['exact', 'icontains'],
            
            # Date fields
            'split_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_split_type_display(self, info):
        """Resolve human-readable split type display."""
        return dict(OrderSplit.split_type.field.choices).get(self.split_type, self.split_type)
    
    def resolve_parent_order_details(self, info):
        """Resolve parent order details."""
        return self.parent_order
    
    def resolve_child_order_details(self, info):
        """Resolve child order details."""
        return self.child_order
    
    def resolve_split_by_details(self, info):
        """Resolve user who performed the split."""
        return self.split_by


class OrderMergeNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Merge.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    merge_type_display = String(description="Human-readable merge type display")
    source_order_count = Int(description="Number of source orders")
    source_order_numbers = List(Int, description="Source order numbers")
    
    class Meta:
        model = OrderMerge
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'target_order': ['exact'],
            'merged_by': ['exact'],
            
            # String fields
            'merge_type': ['exact'],
            'merge_reason': ['exact', 'icontains'],
            
            # Date fields
            'merged_at': ['exact', 'gte', 'lte'],
        }
        
    
    def resolve_merge_type_display(self, info):
        """Resolve human-readable merge type display."""
        return dict(OrderMerge.merge_type.field.choices).get(self.merge_type, self.merge_type)
    
    def resolve_source_order_count(self, info):
        """Resolve number of source orders."""
        return self.source_orders.count()
    
    def resolve_source_order_numbers(self, info):
        """Resolve source order numbers."""
        return [order.number for order in self.source_orders.all()]
    
    def resolve_source_orders(self, info):
        """Resolve source orders."""
        return self.source_orders.all()
    
    def resolve_target_order_details(self, info):
        """Resolve target order details."""
        return self.target_order
    
    def resolve_merged_by_details(self, info):
        """Resolve user who performed the merge."""
        return self.merged_by


class OrderTrackingEventNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Tracking Event.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    event_type_display = String(description="Human-readable event type display")
    has_location = Boolean(description="Whether event has location coordinates")
    is_delivery_event = Boolean(description="Whether event is a delivery-related event")
    

    class Meta:
        model = OrderTrackingEvent
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            
            # String fields
            'event_type': ['exact'],
            'location': ['exact', 'icontains'],
            'carrier': ['exact', 'icontains'],
            'tracking_number': ['exact', 'icontains'],
            
            # Numeric fields
            'latitude': ['exact', 'gte', 'lte', 'isnull'],
            'longitude': ['exact', 'gte', 'lte', 'isnull'],
            
            # Date fields
            'event_timestamp': ['exact', 'gte', 'lte'],
            'estimated_delivery': ['exact', 'gte', 'lte', 'isnull'],
            'actual_delivery': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_event_type_display(self, info):
        """Resolve human-readable event type display."""
        return dict(OrderTrackingEvent.EVENT_TYPES).get(self.event_type, self.event_type)
    
    def resolve_has_location(self, info):
        """Resolve whether event has location coordinates."""
        return self.latitude is not None and self.longitude is not None
    
    def resolve_is_delivery_event(self, info):
        """Resolve whether event is a delivery-related event."""
        delivery_events = [
            "OUT_FOR_DELIVERY",
            "DELIVERED",
            "DELIVERY_ATTEMPTED",
            "DELIVERY_FAILED",
        ]
        return self.event_type in delivery_events
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order


class OrderFraudAssessmentNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Fraud Assessment.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    risk_level_display = String(description="Human-readable risk level display")
    risk_score_display = String(description="Formatted risk score")
    is_high_risk = Boolean(description="Whether order is high risk")
    is_very_high_risk = Boolean(description="Whether order is very high risk")
    is_blocked = Boolean(description="Whether order is blocked")
    requires_review = Boolean(description="Whether review is required")
    

    class Meta:
        model = OrderFraudAssessment
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            'assessed_by': ['exact'],
            'reviewed_by': ['exact'],
            
            # String fields
            'risk_level': ['exact'],
            'assessment_reason': ['exact', 'icontains'],
            'model_version': ['exact', 'icontains'],
            
            # Numeric fields
            'risk_score': ['exact', 'gte', 'lte'],
            'velocity_score': ['exact', 'gte', 'lte'],
            'geo_risk_score': ['exact', 'gte', 'lte'],
            'ip_risk_score': ['exact', 'gte', 'lte'],
            'device_risk_score': ['exact', 'gte', 'lte'],
            'behavioral_risk_score': ['exact', 'gte', 'lte'],
            'model_confidence': ['exact', 'gte', 'lte'],
            
            # Boolean fields
            'is_email_verified': ['exact'],
            'is_phone_verified': ['exact'],
            'is_address_verified': ['exact'],
            'is_payment_verified': ['exact'],
            'review_required': ['exact'],
            
            # Date fields
            'assessed_at': ['exact', 'gte', 'lte'],
            'reviewed_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        ordering = [
            '-assessed_at',
            '-id',
        ]
    
    def resolve_risk_level_display(self, info):
        """Resolve human-readable risk level display."""
        return dict(OrderFraudAssessment.RISK_LEVELS).get(self.risk_level, self.risk_level)
    
    def resolve_risk_score_display(self, info):
        """Resolve formatted risk score."""
        if self.risk_score:
            return f"{float(self.risk_score):.1f}"
        return None
    
    def resolve_is_high_risk(self, info):
        """Resolve whether order is high risk."""
        return self.risk_level == "HIGH"
    
    def resolve_is_very_high_risk(self, info):
        """Resolve whether order is very high risk."""
        return self.risk_level == "VERY_HIGH"
    
    def resolve_is_blocked(self, info):
        """Resolve whether order is blocked."""
        return self.risk_level == "BLOCKED"
    
    def resolve_requires_review(self, info):
        """Resolve whether review is required."""
        return self.review_required
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order
    
    def resolve_assessed_by_details(self, info):
        """Resolve user who performed the assessment."""
        return self.assessed_by
    
    def resolve_reviewed_by_details(self, info):
        """Resolve user who reviewed the assessment."""
        return self.reviewed_by


class OrderPromiseNode(OptimizedDjangoObjectType):
    """
    GraphQL Node for Order Promise.
    """
    
    # ============================================================
    # Calculated Properties
    # ============================================================
    
    promise_type_display = String(description="Human-readable promise type display")
    is_met_status = String(description="Status of the promise (Met, Broken, Pending)")
    compensation_display = String(description="Formatted compensation amount")
    days_to_promise = Int(description="Days until promise expires")
    days_overdue = Int(description="Days overdue if promise is broken")
    
    
    class Meta:
        model = OrderPromise
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            # Foreign keys
            'order': ['exact'],
            
            # String fields
            'promise_type': ['exact'],
            'promised_value': ['exact', 'icontains'],
            'actual_value': ['exact', 'icontains'],
            'broken_reason': ['exact', 'icontains'],
            'compensation_type': ['exact', 'icontains'],
            
            # Numeric fields
            'compensation_amount': ['exact', 'gte', 'lte', 'isnull'],
            
            # Boolean fields
            'is_met': ['exact', 'isnull'],
            'compensation_applied': ['exact'],
            
            # Date fields
            'promised_by': ['exact', 'gte', 'lte'],
            'fulfilled_at': ['exact', 'gte', 'lte', 'isnull'],
        }
        
    
    def resolve_promise_type_display(self, info):
        """Resolve human-readable promise type display."""
        return dict(OrderPromise.PROMISE_TYPES).get(self.promise_type, self.promise_type)
    
    def resolve_is_met_status(self, info):
        """Resolve status of the promise (Met, Broken, Pending)."""
        if self.is_met is True:
            return "Met"
        elif self.is_met is False:
            return "Broken"
        return "Pending"
    
    def resolve_compensation_display(self, info):
        """Resolve formatted compensation amount."""
        if self.compensation_amount:
            return f"${self.compensation_amount:,.2f}"
        return None
    
    def resolve_days_to_promise(self, info):
        """Resolve days until promise expires."""
        if self.is_met is not None:
            return 0
        now = timezone.now()
        if self.promised_by > now:
            return (self.promised_by - now).days
        return 0
    
    def resolve_days_overdue(self, info):
        """Resolve days overdue if promise is broken."""
        if self.is_met is False and self.promised_by:
            now = timezone.now()
            return max(0, (now - self.promised_by).days)
        return 0
    
    def resolve_order_details(self, info):
        """Resolve order details."""
        return self.order