from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from graphql import GraphQLError

from graphq.investors.mutations import CreateInvestment
from investors.models import InvestmentCommitment


class CreateInvestmentMutationTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(
            pk=10,
            is_authenticated=True,
        )

        self.opportunity = SimpleNamespace(pk=20)
        self.plan = SimpleNamespace(pk=30)

        self.commitment = SimpleNamespace(
            pk=40,
            investor=self.user,
            investor_id=self.user.pk,
            opportunity=self.opportunity,
            plan=self.plan,
            amount=Decimal("5000.00"),
            currency="NGN",
            status=InvestmentCommitment.Status.FUNDED,
        )

        self.investment = SimpleNamespace(
            pk=50,
            reference="INV-000001",
        )

        self.info = SimpleNamespace(
            context=SimpleNamespace(user=self.user)
        )

    @patch("graphq.investors.mutations.InvestmentService.create")
    @patch(
        "graphq.investors.mutations."
        "get_investment_commitment_from_global_id"
    )
    def test_create_investment_from_funded_commitment(
        self,
        resolve_commitment,
        create_investment,
    ):
        resolve_commitment.return_value = self.commitment
        create_investment.return_value = self.investment

        payload = CreateInvestment.mutate_and_get_payload(
            None,
            self.info,
            commitment_id="commitment-global-id",
            reference="INV-000001",
            client_mutation_id="client-001",
        )

        resolve_commitment.assert_called_once_with(
            "commitment-global-id"
        )

        create_investment.assert_called_once_with(
            investor=self.user,
            opportunity=self.opportunity,
            plan=self.plan,
            commitment=self.commitment,
            reference="INV-000001",
            amount=Decimal("5000.00"),
            currency="NGN",
        )

        self.assertIs(payload.investment, self.investment)
        self.assertEqual(
            payload.client_mutation_id,
            "client-001",
        )

    @patch("graphq.investors.mutations.InvestmentService.create")
    @patch(
        "graphq.investors.mutations."
        "get_investment_commitment_from_global_id"
    )
    def test_anonymous_user_cannot_create_investment(
        self,
        resolve_commitment,
        create_investment,
    ):
        self.info.context.user.is_authenticated = False

        with self.assertRaisesMessage(
            GraphQLError,
            "Authentication required.",
        ):
            CreateInvestment.mutate_and_get_payload(
                None,
                self.info,
                commitment_id="commitment-global-id",
                reference="INV-000001",
            )

        resolve_commitment.assert_not_called()
        create_investment.assert_not_called()

    @patch("graphq.investors.mutations.InvestmentService.create")
    @patch(
        "graphq.investors.mutations."
        "get_investment_commitment_from_global_id"
    )
    def test_invalid_commitment_id_prevents_creation(
        self,
        resolve_commitment,
        create_investment,
    ):
        resolve_commitment.side_effect = GraphQLError(
            "Invalid investment commitment ID."
        )

        with self.assertRaisesMessage(
            GraphQLError,
            "Invalid investment commitment ID.",
        ):
            CreateInvestment.mutate_and_get_payload(
                None,
                self.info,
                commitment_id="invalid-global-id",
                reference="INV-000001",
            )

        create_investment.assert_not_called()

    @patch("graphq.investors.mutations.InvestmentService.create")
    @patch(
        "graphq.investors.mutations."
        "get_investment_commitment_from_global_id"
    )
    def test_user_cannot_use_another_users_commitment(
        self,
        resolve_commitment,
        create_investment,
    ):
        other_user = SimpleNamespace(pk=99)

        self.commitment.investor = other_user
        self.commitment.investor_id = other_user.pk
        resolve_commitment.return_value = self.commitment

        with self.assertRaisesMessage(
            GraphQLError,
            "You do not have permission to invest using this commitment.",
        ):
            CreateInvestment.mutate_and_get_payload(
                None,
                self.info,
                commitment_id="commitment-global-id",
                reference="INV-000001",
            )

        create_investment.assert_not_called()

    @patch("graphq.investors.mutations.InvestmentService.create")
    @patch(
        "graphq.investors.mutations."
        "get_investment_commitment_from_global_id"
    )
    def test_unfunded_commitment_is_rejected_by_domain_service(
        self,
        resolve_commitment,
        create_investment,
    ):
        self.commitment.status = InvestmentCommitment.Status.PENDING
        resolve_commitment.return_value = self.commitment

        create_investment.side_effect = ValidationError(
            {
                "commitment": (
                    "An investment can only be created from "
                    "a funded commitment."
                )
            }
        )

        with self.assertRaises(ValidationError):
            CreateInvestment.mutate_and_get_payload(
                None,
                self.info,
                commitment_id="commitment-global-id",
                reference="INV-000001",
            )

        create_investment.assert_called_once()
