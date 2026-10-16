"""
Tests for InvestmentPlan GraphQL mutations.

These tests exercise the GraphQL adapter contract directly:
- authentication is required;
- Relay opportunity/plan IDs are passed through the ID resolvers;
- mutations delegate business operations to PlanService;
- the payload returns the plan and client_mutation_id;
- updates require at least one supplied field.

Run with:
    python manage.py test graphq.investors.tests.test_plan_mutations
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from graphql import GraphQLError

from investors.models import InvestmentPlan
from graphq.investors.types import InvestmentPlanNode
from graphq.investors.mutations import (
    ActivateInvestmentPlan,
    CancelInvestmentPlan,
    CloseInvestmentPlan,
    CreateInvestmentPlan,
    PauseInvestmentPlan,
    UpdateInvestmentPlan,
)


MUTATIONS_MODULE = "graphq.investors.mutations"


class InvestmentPlanMutationTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_authenticated=True)
        self.info = SimpleNamespace(context=SimpleNamespace(user=self.user))
        self.opportunity = SimpleNamespace(id=17)
        self.plan = SimpleNamespace(id=29, reference="PLAN-001")

    def test_create_investment_plan_delegates_to_service_and_returns_payload(self):
        with (
            patch(
                f"{MUTATIONS_MODULE}.get_investment_opportunity_from_global_id",
                return_value=self.opportunity,
            ) as resolve_opportunity,
            patch(
                f"{MUTATIONS_MODULE}.PlanService.create",
                return_value=self.plan,
            ) as create_plan,
        ):
            payload = CreateInvestmentPlan.mutate_and_get_payload(
                None,
                self.info,
                opportunity_id="SW52ZXN0bWVudE9wcG9ydHVuaXR5OjE3",
                reference="PLAN-001",
                name="Starter Plan",
                description="A starter investment plan",
                minimum_amount=Decimal("10000.00"),
                maximum_amount=Decimal("100000.00"),
                duration_days=90,
                expected_return_rate=Decimal("0.0500"),
                metadata={"source": "test"},
                client_mutation_id="client-create-1",
            )

        resolve_opportunity.assert_called_once_with(
            "SW52ZXN0bWVudE9wcG9ydHVuaXR5OjE3"
        )
        create_plan.assert_called_once_with(
            opportunity=self.opportunity,
            reference="PLAN-001",
            name="Starter Plan",
            description="A starter investment plan",
            minimum_amount=Decimal("10000.00"),
            maximum_amount=Decimal("100000.00"),
            duration_days=90,
            expected_return_rate=Decimal("0.0500"),
            metadata={"source": "test"},
        )
        self.assertIs(payload.investment_plan, self.plan)
        self.assertEqual(payload.client_mutation_id, "client-create-1")

    def test_create_investment_plan_rejects_anonymous_user(self):
        self.user.is_authenticated = False

        with patch(f"{MUTATIONS_MODULE}.PlanService.create") as create_plan:
            with self.assertRaisesMessage(
                GraphQLError, "Authentication required."
            ):
                CreateInvestmentPlan.mutate_and_get_payload(
                    None,
                    self.info,
                    opportunity_id="some-global-id",
                    reference="PLAN-001",
                    name="Starter Plan",
                    minimum_amount=Decimal("10000.00"),
                )

        create_plan.assert_not_called()

    def test_update_investment_plan_delegates_supplied_fields(self):
        updates = {
            "name": "Updated Plan",
            "maximum_amount": Decimal("250000.00"),
            "duration_days": 180,
        }

        with (
            patch(
                f"{MUTATIONS_MODULE}.get_node_instance",
                return_value=self.plan,
            ) as resolve_plan,
            patch(
                f"{MUTATIONS_MODULE}.PlanService.update",
                return_value=self.plan,
            ) as update_plan,
        ):
            payload = UpdateInvestmentPlan.mutate_and_get_payload(
                None,
                self.info,
                id="SW52ZXN0bWVudFBsYW46Mjk=",
                **updates,
                client_mutation_id="client-update-1",
            )

        resolve_plan.assert_called_once_with(
            "SW52ZXN0bWVudFBsYW46Mjk=",
            node_type=InvestmentPlanNode,
            model=InvestmentPlan,
            invalid_id_message="Invalid investment plan ID.",
            not_found_message="Investment plan not found.",
        )
        update_plan.assert_called_once_with(self.plan, **updates)
        self.assertIs(payload.investment_plan, self.plan)
        self.assertEqual(payload.client_mutation_id, "client-update-1")

    def test_update_investment_plan_requires_at_least_one_field(self):
        with (
            patch(
                f"{MUTATIONS_MODULE}.get_node_instance",
                return_value=self.plan,
            ),
            patch(f"{MUTATIONS_MODULE}.PlanService.update") as update_plan,
        ):
            with self.assertRaisesMessage(
                GraphQLError,
                "At least one field must be provided for update.",
            ):
                UpdateInvestmentPlan.mutate_and_get_payload(
                    None,
                    self.info,
                    id="SW52ZXN0bWVudFBsYW46Mjk=",
                )

        update_plan.assert_not_called()

    def test_update_investment_plan_rejects_anonymous_user(self):
        self.user.is_authenticated = False

        with (
            patch(f"{MUTATIONS_MODULE}.get_node_instance") as resolve_plan,
            patch(f"{MUTATIONS_MODULE}.PlanService.update") as update_plan,
        ):
            with self.assertRaisesMessage(
                GraphQLError, "Authentication required."
            ):
                UpdateInvestmentPlan.mutate_and_get_payload(
                    None,
                    self.info,
                    id="SW52ZXN0bWVudFBsYW46Mjk=",
                    name="Updated Plan",
                )

        resolve_plan.assert_not_called()
        update_plan.assert_not_called()

    def test_lifecycle_mutations_delegate_to_the_matching_service_method(self):
        cases = (
            (ActivateInvestmentPlan, "activate", "client-activate-1"),
            (PauseInvestmentPlan, "pause", "client-pause-1"),
            (CloseInvestmentPlan, "close", "client-close-1"),
            (CancelInvestmentPlan, "cancel", "client-cancel-1"),
        )

        for mutation_class, service_method, client_mutation_id in cases:
            with self.subTest(mutation=mutation_class.__name__):
                self.user.is_authenticated = True
                with (
                    patch(
                        f"{MUTATIONS_MODULE}.get_node_instance",
                        return_value=self.plan,
                    ) as resolve_plan,
                    patch(
                        f"{MUTATIONS_MODULE}.PlanService.{service_method}",
                        return_value=self.plan,
                    ) as transition,
                ):
                    payload = mutation_class.mutate_and_get_payload(
                        None,
                        self.info,
                        id="SW52ZXN0bWVudFBsYW46Mjk=",
                        client_mutation_id=client_mutation_id,
                    )

                resolve_plan.assert_called_once()
                transition.assert_called_once_with(self.plan)
                self.assertIs(payload.investment_plan, self.plan)
                self.assertEqual(
                    payload.client_mutation_id, client_mutation_id
                )

    def test_lifecycle_mutations_reject_anonymous_user(self):
        lifecycle_mutations = (
            ActivateInvestmentPlan,
            PauseInvestmentPlan,
            CloseInvestmentPlan,
            CancelInvestmentPlan,
        )

        self.user.is_authenticated = False

        for mutation_class in lifecycle_mutations:
            with self.subTest(mutation=mutation_class.__name__):
                with patch(
                    f"{MUTATIONS_MODULE}.get_node_instance"
                ) as resolve_plan:
                    with self.assertRaisesMessage(
                        GraphQLError, "Authentication required."
                    ):
                        mutation_class.mutate_and_get_payload(
                            None,
                            self.info,
                            id="SW52ZXN0bWVudFBsYW46Mjk=",
                        )

                resolve_plan.assert_not_called()
