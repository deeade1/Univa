"""
Tests for InvestmentCommitment GraphQL lifecycle mutations.

These tests exercise the GraphQL adapter contract:
- authentication is required;
- commitment Relay IDs are resolved;
- lifecycle operations delegate to InvestmentCommitmentLifecycle;
- lifecycle errors propagate to the caller;
- the commitment and client_mutation_id are returned.

Run with:
    python manage.py test graphq.investors.tests.test_commitment_lifecycle_mutations
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from graphql import GraphQLError

from graphq.investors.mutations import (
    CancelInvestmentCommitment,
    ConfirmInvestmentCommitment,
    ExpireInvestmentCommitment,
    FundInvestmentCommitment,
)


MUTATIONS_MODULE = "graphq.investors.mutations"
LIFECYCLE_MODULE = (
    f"{MUTATIONS_MODULE}.InvestmentCommitmentLifecycle"
)


class InvestmentCommitmentLifecycleMutationTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_authenticated=True)
        self.info = SimpleNamespace(
            context=SimpleNamespace(user=self.user)
        )

        self.commitment = SimpleNamespace(
            id=41,
            reference="COMMIT-INVEST-001",
            amount=Decimal("500000.00"),
            currency="NGN",
            status="PENDING",
        )

        self.commitment_id = "SW52ZXN0bWVudENvbW1pdG1lbnQ6NDE="

    def assert_lifecycle_mutation_succeeds(
        self,
        mutation_class,
        lifecycle_method,
        client_mutation_id,
    ):
        with (
            patch(
                f"{MUTATIONS_MODULE}."
                "get_investment_commitment_from_global_id",
                return_value=self.commitment,
            ) as resolve_commitment,
            patch(
                f"{LIFECYCLE_MODULE}.{lifecycle_method}",
                return_value=self.commitment,
            ) as lifecycle_operation,
        ):
            payload = mutation_class.mutate_and_get_payload(
                None,
                self.info,
                id=self.commitment_id,
                client_mutation_id=client_mutation_id,
            )

        resolve_commitment.assert_called_once_with(self.commitment_id)
        lifecycle_operation.assert_called_once_with(self.commitment)

        self.assertIs(
            payload.investment_commitment,
            self.commitment,
        )
        self.assertEqual(
            payload.client_mutation_id,
            client_mutation_id,
        )

    def assert_anonymous_user_rejected(
        self,
        mutation_class,
        lifecycle_method,
    ):
        self.user.is_authenticated = False

        with (
            patch(
                f"{MUTATIONS_MODULE}."
                "get_investment_commitment_from_global_id"
            ) as resolve_commitment,
            patch(
                f"{LIFECYCLE_MODULE}.{lifecycle_method}"
            ) as lifecycle_operation,
        ):
            with self.assertRaisesMessage(
                GraphQLError,
                "Authentication required.",
            ):
                mutation_class.mutate_and_get_payload(
                    None,
                    self.info,
                    id=self.commitment_id,
                )

        resolve_commitment.assert_not_called()
        lifecycle_operation.assert_not_called()

    def assert_invalid_id_rejected(
        self,
        mutation_class,
        lifecycle_method,
    ):
        with (
            patch(
                f"{MUTATIONS_MODULE}."
                "get_investment_commitment_from_global_id",
                side_effect=GraphQLError(
                    "Invalid investment commitment ID."
                ),
            ) as resolve_commitment,
            patch(
                f"{LIFECYCLE_MODULE}.{lifecycle_method}"
            ) as lifecycle_operation,
        ):
            with self.assertRaisesMessage(
                GraphQLError,
                "Invalid investment commitment ID.",
            ):
                mutation_class.mutate_and_get_payload(
                    None,
                    self.info,
                    id="invalid-commitment-id",
                )

        resolve_commitment.assert_called_once_with(
            "invalid-commitment-id"
        )
        lifecycle_operation.assert_not_called()

    def assert_lifecycle_error_propagates(
        self,
        mutation_class,
        lifecycle_method,
    ):
        validation_error = ValidationError(
            {
                "status": (
                    "Investment commitment cannot transition "
                    "from 'FUNDED'."
                )
            }
        )

        with (
            patch(
                f"{MUTATIONS_MODULE}."
                "get_investment_commitment_from_global_id",
                return_value=self.commitment,
            ),
            patch(
                f"{LIFECYCLE_MODULE}.{lifecycle_method}",
                side_effect=validation_error,
            ) as lifecycle_operation,
        ):
            with self.assertRaises(ValidationError) as context:
                mutation_class.mutate_and_get_payload(
                    None,
                    self.info,
                    id=self.commitment_id,
                )

        self.assertIs(context.exception, validation_error)
        lifecycle_operation.assert_called_once_with(self.commitment)

    # ---------------------------------------------------------------
    # Confirm
    # ---------------------------------------------------------------

    def test_confirm_commitment_succeeds(self):
        self.assert_lifecycle_mutation_succeeds(
            ConfirmInvestmentCommitment,
            "confirm",
            "client-confirm-commitment-1",
        )

    def test_confirm_commitment_rejects_anonymous_user(self):
        self.assert_anonymous_user_rejected(
            ConfirmInvestmentCommitment,
            "confirm",
        )

    def test_confirm_commitment_rejects_invalid_id(self):
        self.assert_invalid_id_rejected(
            ConfirmInvestmentCommitment,
            "confirm",
        )

    def test_confirm_commitment_propagates_lifecycle_error(self):
        self.assert_lifecycle_error_propagates(
            ConfirmInvestmentCommitment,
            "confirm",
        )

    # ---------------------------------------------------------------
    # Fund
    # ---------------------------------------------------------------

    def test_fund_commitment_succeeds(self):
        self.assert_lifecycle_mutation_succeeds(
            FundInvestmentCommitment,
            "fund",
            "client-fund-commitment-1",
        )

    def test_fund_commitment_rejects_anonymous_user(self):
        self.assert_anonymous_user_rejected(
            FundInvestmentCommitment,
            "fund",
        )

    def test_fund_commitment_rejects_invalid_id(self):
        self.assert_invalid_id_rejected(
            FundInvestmentCommitment,
            "fund",
        )

    def test_fund_commitment_propagates_lifecycle_error(self):
        self.assert_lifecycle_error_propagates(
            FundInvestmentCommitment,
            "fund",
        )

    # ---------------------------------------------------------------
    # Cancel
    # ---------------------------------------------------------------

    def test_cancel_commitment_succeeds(self):
        self.assert_lifecycle_mutation_succeeds(
            CancelInvestmentCommitment,
            "cancel",
            "client-cancel-commitment-1",
        )

    def test_cancel_commitment_rejects_anonymous_user(self):
        self.assert_anonymous_user_rejected(
            CancelInvestmentCommitment,
            "cancel",
        )

    def test_cancel_commitment_rejects_invalid_id(self):
        self.assert_invalid_id_rejected(
            CancelInvestmentCommitment,
            "cancel",
        )

    def test_cancel_commitment_propagates_lifecycle_error(self):
        self.assert_lifecycle_error_propagates(
            CancelInvestmentCommitment,
            "cancel",
        )

    # ---------------------------------------------------------------
    # Expire
    # ---------------------------------------------------------------

    def test_expire_commitment_succeeds(self):
        self.assert_lifecycle_mutation_succeeds(
            ExpireInvestmentCommitment,
            "expire",
            "client-expire-commitment-1",
        )

    def test_expire_commitment_rejects_anonymous_user(self):
        self.assert_anonymous_user_rejected(
            ExpireInvestmentCommitment,
            "expire",
        )

    def test_expire_commitment_rejects_invalid_id(self):
        self.assert_invalid_id_rejected(
            ExpireInvestmentCommitment,
            "expire",
        )

    def test_expire_commitment_propagates_lifecycle_error(self):
        self.assert_lifecycle_error_propagates(
            ExpireInvestmentCommitment,
            "expire",
        )
