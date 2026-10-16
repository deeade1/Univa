from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from graphql import GraphQLError
from graphql_relay import to_global_id

from accounts.models import User
from investors.models import InvestmentOpportunity

from graphq.investors.mutations import (
    CreateInvestmentOpportunity,
    UpdateInvestmentOpportunity,
    OpenInvestmentOpportunity,
    PauseInvestmentOpportunity,
    CloseInvestmentOpportunity,
    CancelInvestmentOpportunity,
)
from graphq.investors.types import InvestmentOpportunityNode


class InvestmentOpportunityMutationTestCase(TestCase):
    def create_user(self, email="opportunity@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_info(self, user):
        return SimpleNamespace(
            context=SimpleNamespace(user=user),
        )

    def create_opportunity(
        self,
        reference="OPP-0001",
        name="Test Opportunity",
        status=InvestmentOpportunity.Status.DRAFT,
    ):
        return InvestmentOpportunity.objects.create(
            reference=reference,
            name=name,
            description="Test investment opportunity",
            currency="NGN",
            minimum_amount=Decimal("1000.00"),
            maximum_amount=Decimal("100000.00"),
            status=status,
            metadata={"source": "test"},
        )

    def global_id(self, opportunity):
        return to_global_id(
            InvestmentOpportunityNode._meta.name,
            opportunity.pk,
        )

    def assert_requires_authentication(
        self,
        mutation,
        service_path,
        **input_data,
    ):
        anonymous_user = SimpleNamespace(
            is_authenticated=False,
        )
        info = self.create_info(anonymous_user)

        with patch(service_path) as service_method:
            with self.assertRaises(GraphQLError) as raised:
                mutation.mutate_and_get_payload(
                    None,
                    info,
                    **input_data,
                )

        self.assertEqual(
            str(raised.exception),
            "Authentication required.",
        )
        service_method.assert_not_called()

    # ---------------------------------------------------------
    # CreateInvestmentOpportunity
    # ---------------------------------------------------------

    @patch(
        "graphq.investors.mutations.OpportunityService.create"
    )
    def test_create_opportunity_delegates_to_service(self, create):
        user = self.create_user()
        info = self.create_info(user)

        opportunity = InvestmentOpportunity(
            reference="OPP-0001",
            name="New Opportunity",
            description="Investment description",
            currency="NGN",
            minimum_amount=Decimal("1000.00"),
            maximum_amount=Decimal("100000.00"),
            metadata={"source": "test"},
        )
        create.return_value = opportunity

        result = CreateInvestmentOpportunity.mutate_and_get_payload(
            None,
            info,
            reference="OPP-0001",
            name="New Opportunity",
            description="Investment description",
            currency="NGN",
            minimum_amount=Decimal("1000.00"),
            maximum_amount=Decimal("100000.00"),
            metadata={"source": "test"},
            client_mutation_id="create-opportunity-1",
        )

        self.assertIs(result.investment_opportunity, opportunity)

        create.assert_called_once_with(
            reference="OPP-0001",
            name="New Opportunity",
            description="Investment description",
            currency="NGN",
            minimum_amount=Decimal("1000.00"),
            maximum_amount=Decimal("100000.00"),
            metadata={"source": "test"},
        )

        self.assertEqual(
            result.client_mutation_id,
            "create-opportunity-1",
        )

    @patch(
        "graphq.investors.mutations.OpportunityService.create"
    )
    def test_create_opportunity_requires_authentication(self, create):
        self.assert_requires_authentication(
            CreateInvestmentOpportunity,
            "graphq.investors.mutations.OpportunityService.create",
            reference="OPP-0001",
            name="New Opportunity",
            minimum_amount=Decimal("1000.00"),
        )

        create.assert_not_called()

    # ---------------------------------------------------------
    # UpdateInvestmentOpportunity
    # ---------------------------------------------------------

    @patch(
        "graphq.investors.mutations.OpportunityService.update"
    )
    def test_update_opportunity_delegates_to_service(self, update):
        user = self.create_user()
        info = self.create_info(user)
        opportunity = self.create_opportunity()

        update.return_value = opportunity

        result = UpdateInvestmentOpportunity.mutate_and_get_payload(
            None,
            info,
            id=self.global_id(opportunity),
            name="Updated Opportunity",
            description="Updated description",
            client_mutation_id="update-opportunity-1",
        )

        self.assertIs(result.investment_opportunity, opportunity)

        update.assert_called_once_with(
            opportunity,
            name="Updated Opportunity",
            description="Updated description",
        )

        self.assertEqual(
            result.client_mutation_id,
            "update-opportunity-1",
        )

    @patch(
        "graphq.investors.mutations.OpportunityService.update"
    )
    def test_update_opportunity_requires_authentication(self, update):
        opportunity = self.create_opportunity()

        self.assert_requires_authentication(
            UpdateInvestmentOpportunity,
            "graphq.investors.mutations.OpportunityService.update",
            id=self.global_id(opportunity),
            name="Updated Opportunity",
        )

        update.assert_not_called()

    @patch(
        "graphq.investors.mutations.OpportunityService.update"
    )
    def test_update_opportunity_rejects_wrong_node_type(self, update):
        user = self.create_user()
        info = self.create_info(user)
        opportunity = self.create_opportunity()

        wrong_global_id = to_global_id(
            "InvestorNode",
            opportunity.pk,
        )

        with self.assertRaises(GraphQLError) as raised:
            UpdateInvestmentOpportunity.mutate_and_get_payload(
                None,
                info,
                id=wrong_global_id,
                name="Updated Opportunity",
            )

        self.assertEqual(
            str(raised.exception),
            "Invalid investment opportunity ID.",
        )
        update.assert_not_called()

    # ---------------------------------------------------------
    # OpenInvestmentOpportunity
    # ---------------------------------------------------------

    @patch(
        "graphq.investors.mutations.OpportunityService.open"
    )
    def test_open_opportunity_delegates_to_service(self, open_service):
        user = self.create_user()
        info = self.create_info(user)
        opportunity = self.create_opportunity()

        open_service.return_value = opportunity

        result = OpenInvestmentOpportunity.mutate_and_get_payload(
            None,
            info,
            id=self.global_id(opportunity),
            client_mutation_id="open-opportunity-1",
        )

        self.assertIs(result.investment_opportunity, opportunity)
        open_service.assert_called_once_with(opportunity)

        self.assertEqual(
            result.client_mutation_id,
            "open-opportunity-1",
        )

    @patch(
        "graphq.investors.mutations.OpportunityService.open"
    )
    def test_open_opportunity_requires_authentication(self, open_service):
        opportunity = self.create_opportunity()

        self.assert_requires_authentication(
            OpenInvestmentOpportunity,
            "graphq.investors.mutations.OpportunityService.open",
            id=self.global_id(opportunity),
        )

        open_service.assert_not_called()

    # ---------------------------------------------------------
    # PauseInvestmentOpportunity
    # ---------------------------------------------------------

    @patch(
        "graphq.investors.mutations.OpportunityService.pause"
    )
    def test_pause_opportunity_delegates_to_service(self, pause):
        user = self.create_user()
        info = self.create_info(user)
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        pause.return_value = opportunity

        result = PauseInvestmentOpportunity.mutate_and_get_payload(
            None,
            info,
            id=self.global_id(opportunity),
            client_mutation_id="pause-opportunity-1",
        )

        self.assertIs(result.investment_opportunity, opportunity)
        pause.assert_called_once_with(opportunity)

        self.assertEqual(
            result.client_mutation_id,
            "pause-opportunity-1",
        )

    @patch(
        "graphq.investors.mutations.OpportunityService.pause"
    )
    def test_pause_opportunity_requires_authentication(self, pause):
        opportunity = self.create_opportunity()

        self.assert_requires_authentication(
            PauseInvestmentOpportunity,
            "graphq.investors.mutations.OpportunityService.pause",
            id=self.global_id(opportunity),
        )

        pause.assert_not_called()

    # ---------------------------------------------------------
    # CloseInvestmentOpportunity
    # ---------------------------------------------------------

    @patch(
        "graphq.investors.mutations.OpportunityService.close"
    )
    def test_close_opportunity_delegates_to_service(self, close):
        user = self.create_user()
        info = self.create_info(user)
        opportunity = self.create_opportunity(
            status=InvestmentOpportunity.Status.OPEN,
        )

        close.return_value = opportunity

        result = CloseInvestmentOpportunity.mutate_and_get_payload(
            None,
            info,
            id=self.global_id(opportunity),
            client_mutation_id="close-opportunity-1",
        )

        self.assertIs(result.investment_opportunity, opportunity)
        close.assert_called_once_with(opportunity)

        self.assertEqual(
            result.client_mutation_id,
            "close-opportunity-1",
        )

    @patch(
        "graphq.investors.mutations.OpportunityService.close"
    )
    def test_close_opportunity_requires_authentication(self, close):
        opportunity = self.create_opportunity()

        self.assert_requires_authentication(
            CloseInvestmentOpportunity,
            "graphq.investors.mutations.OpportunityService.close",
            id=self.global_id(opportunity),
        )

        close.assert_not_called()

    # ---------------------------------------------------------
    # CancelInvestmentOpportunity
    # ---------------------------------------------------------

    @patch(
        "graphq.investors.mutations.OpportunityService.cancel"
    )
    def test_cancel_opportunity_delegates_to_service(self, cancel):
        user = self.create_user()
        info = self.create_info(user)
        opportunity = self.create_opportunity()

        cancel.return_value = opportunity

        result = CancelInvestmentOpportunity.mutate_and_get_payload(
            None,
            info,
            id=self.global_id(opportunity),
            client_mutation_id="cancel-opportunity-1",
        )

        self.assertIs(result.investment_opportunity, opportunity)
        cancel.assert_called_once_with(opportunity)

        self.assertEqual(
            result.client_mutation_id,
            "cancel-opportunity-1",
        )

    @patch(
        "graphq.investors.mutations.OpportunityService.cancel"
    )
    def test_cancel_opportunity_requires_authentication(self, cancel):
        opportunity = self.create_opportunity()

        self.assert_requires_authentication(
            CancelInvestmentOpportunity,
            "graphq.investors.mutations.OpportunityService.cancel",
            id=self.global_id(opportunity),
        )

        cancel.assert_not_called()
