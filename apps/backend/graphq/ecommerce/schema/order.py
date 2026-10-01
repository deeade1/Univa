import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q
from django.utils import timezone

from graphq.ecommerce.types.order import (
    OrderLineNode,
    FulfillmentNode,
    FulfillmentLineNode,
    OrderEventNode,
    OrderNode,
    OrderGrantedRefundNode,
    OrderTrackingEventNode,
    OrderFraudAssessmentNode,
    OrderPerformanceMetricsNode,
    OrderSplitNode,
    OrderMergeNode,
    OrderPromiseNode,
)


# =============================================================================
# Schema Registration
# =============================================================================

class OrderQuery(graphene.ObjectType):
   # Node queries
   order_granted_refund = Node.Field(OrderGrantedRefundNode)
   all_order_granted_refunds = DjangoFilterConnectionField(OrderGrantedRefundNode)
   order_performance_metrics = Node.Field(OrderPerformanceMetricsNode)
   all_order_performance_metrics = DjangoFilterConnectionField(OrderPerformanceMetricsNode)
   order_split = Node.Field(OrderSplitNode)
   all_order_splits = DjangoFilterConnectionField(OrderSplitNode)
   order_merge = Node.Field(OrderMergeNode)
   all_order_merges = DjangoFilterConnectionField(OrderMergeNode)
   order_tracking_event = Node.Field(OrderTrackingEventNode)
   all_order_tracking_events = DjangoFilterConnectionField(OrderTrackingEventNode)
   order_fraud_assessment = Node.Field(OrderFraudAssessmentNode)
   all_order_fraud_assessments = DjangoFilterConnectionField(OrderFraudAssessmentNode)
   order_promise = Node.Field(OrderPromiseNode)
   all_order_promises = DjangoFilterConnectionField(OrderPromiseNode)
   order_performance_metrics = graphene.Field(OrderPerformanceMetricsNode, order_id=graphene.ID(required=True))
   high_risk_orders = DjangoFilterConnectionField(OrderNode)
   orders_requiring_review = DjangoFilterConnectionField(OrderNode)
   order = Node.Field(OrderNode)
   all_orders = DjangoFilterConnectionField(OrderNode)
   order_line = Node.Field(OrderLineNode)
   all_order_lines = DjangoFilterConnectionField(OrderLineNode)
   fulfillment = Node.Field(FulfillmentNode)
   all_fulfillments = DjangoFilterConnectionField(FulfillmentNode)
   fulfillment_line = Node.Field(FulfillmentLineNode)
   all_fulfillment_lines = DjangoFilterConnectionField(FulfillmentLineNode)
   order_event = Node.Field(OrderEventNode)
   all_order_events = DjangoFilterConnectionField(OrderEventNode)
 
  
   