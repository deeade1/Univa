# ecommerce/tests/test_models/test_order_hygiene.py

from django.test import SimpleTestCase

from ecommerce.models.order import Order


class TestOrderRemovedFields(SimpleTestCase):
    REMOVED_FIELDS = (
        "use_old_id",
        "customer_satisfaction_score",
        "net_promoter_score",
        "would_repurchase",
        "review_id",
        "fraud_score",
        "fraud_risk_level",
        "requires_manual_review",
        "reviewed_by_fraud_team",
        "acquisition_channel",
        "campaign_id",
        "attribution_model",
        "lifetime_value",
        "carbon_footprint_kg",
        "is_carbon_neutral",
    )

    def test_removed_fields_are_gone(self):
        names = {f.name for f in Order._meta.get_fields()}
        for field in self.REMOVED_FIELDS:
            self.assertNotIn(
                field,
                names,
                f"Order.{field} should have been removed",
            )


class TestOrderKeptFields(SimpleTestCase):
    KEPT_FIELDS = (
        "priority_level",
        "is_prime",
        "is_business",
        "is_express",
        "fulfillment_strategy",
        "preferred_warehouse",
        "promised_delivery_date",
        "actual_delivery_date",
        "delivery_window_start",
        "delivery_window_end",
        "cost_of_goods_sold",
        "fulfillment_cost",
        "shipping_cost_actual",
        "gross_margin",
    )

    def test_kept_fields_present(self):
        names = {f.name for f in Order._meta.get_fields()}
        for field in self.KEPT_FIELDS:
            self.assertIn(
                field,
                names,
                f"Order.{field} should still be present",
            )


class TestOrderConstraints(SimpleTestCase):
    def test_constraints_present(self):
        names = {c.name for c in Order._meta.constraints}
        self.assertIn("order_number_positive", names)
        self.assertIn("order_total_gross_non_negative", names)
        self.assertIn("order_total_net_non_negative", names)


class TestOrderIndexes(SimpleTestCase):
    def test_expected_indexes_present(self):
        names = {i.name for i in Order._meta.indexes}
        for expected in (
            "order_user_created_idx",
            "order_channel_status_idx",
            "order_status_created_idx",
            "order_created_status_idx",
            "order_priority_idx",
            "order_prime_status_idx",
            "order_promised_status_idx",
        ):
            self.assertIn(expected, names)