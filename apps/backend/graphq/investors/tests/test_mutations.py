from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from investors.models import Investor

from graphq.investors.mutations import (
    ActivateInvestor,
    CloseInvestor,
    CreateInvestor,
    SuspendInvestor,
    UpdateInvestor,
)
from graphq.investors.types import InvestorNode
from graphql_relay import to_global_id


class CreateInvestorMutationTestCase(TestCase):
    def create_user(self):
        return User.objects.create_user(
            email="user@example.com",
            password="test-password",
        )

    def create_info(self, user):
        class Context:
            pass

        class Info:
            pass

        context = Context()
        context.user = user

        info = Info()
        info.context = context

        return info

    @patch("graphq.investors.mutations.InvestorService.create")
    def test_create_investor_requires_authentication(
        self,
        create,
    ):
        class AnonymousUser:
            is_authenticated = False

        info = self.create_info(AnonymousUser())

        with self.assertRaises(Exception) as raised:
            CreateInvestor.mutate_and_get_payload(
                None,
                info,
                reference="INV-0001",
                display_name="Test Investor",
                metadata={"source": "test"},
                client_mutation_id="client-1",
            )

        self.assertEqual(
            str(raised.exception),
            "Authentication required.",
        )

        create.assert_not_called()

    @patch("graphq.investors.mutations.InvestorService.create")
    def test_create_investor_delegates_to_service(
        self,
        create,
    ):
        user = self.create_user()
        info = self.create_info(user)

        investor = Investor(
            user=user,
            reference="INV-0001",
            status=Investor.Status.PENDING,
            display_name="Test Investor",
            metadata={"source": "test"},
        )

        create.return_value = investor

        result = CreateInvestor.mutate_and_get_payload(
            None,
            info,
            reference="INV-0001",
            display_name="Test Investor",
            metadata={"source": "test"},
            client_mutation_id="client-1",
        )

        self.assertIs(result.investor, investor)

        create.assert_called_once_with(
            user=user,
            reference="INV-0001",
            display_name="Test Investor",
            metadata={"source": "test"},
        )

    @patch("graphq.investors.mutations.InvestorService.create")
    def test_create_investor_returns_client_mutation_id(
        self,
        create,
    ):
        user = self.create_user()
        info = self.create_info(user)

        investor = Investor(
            user=user,
            reference="INV-0001",
            status=Investor.Status.PENDING,
            display_name="Test Investor",
            metadata={},
        )

        create.return_value = investor

        result = CreateInvestor.mutate_and_get_payload(
            None,
            info,
            reference="INV-0001",
            display_name="Test Investor",
            metadata={},
            client_mutation_id="create-investor-1",
        )

        self.assertEqual(
            result.client_mutation_id,
            "create-investor-1",
        )

    @patch("graphq.investors.mutations.InvestorService.create")
    def test_create_investor_passes_empty_display_name(
        self,
        create,
    ):
        user = self.create_user()
        info = self.create_info(user)

        investor = Investor(
            user=user,
            reference="INV-0001",
            status=Investor.Status.PENDING,
            display_name="",
            metadata={},
        )

        create.return_value = investor

        CreateInvestor.mutate_and_get_payload(
            None,
            info,
            reference="INV-0001",
            client_mutation_id="client-1",
        )

        create.assert_called_once_with(
            user=user,
            reference="INV-0001",
            display_name="",
            metadata=None,
        )

    @patch("graphq.investors.mutations.InvestorService.create")
    def test_create_investor_passes_metadata(
        self,
        create,
    ):
        user = self.create_user()
        info = self.create_info(user)

        metadata = {
            "source": "mobile",
            "campaign": "launch",
        }

        investor = Investor(
            user=user,
            reference="INV-0001",
            status=Investor.Status.PENDING,
            display_name="Mobile Investor",
            metadata=metadata,
        )

        create.return_value = investor

        CreateInvestor.mutate_and_get_payload(
            None,
            info,
            reference="INV-0001",
            display_name="Mobile Investor",
            metadata=metadata,
            client_mutation_id="client-1",
        )

        create.assert_called_once_with(
            user=user,
            reference="INV-0001",
            display_name="Mobile Investor",
            metadata=metadata,
        )
        

class InvestorMutationTestCase(TestCase):
    def create_user(self, email="investor@example.com"):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def create_investor(self, email="investor@example.com"):
        user = self.create_user(email=email)

        return Investor.objects.create(
            user=user,
            reference=f"INV-{user.pk:04d}",
            status=Investor.Status.PENDING,
            display_name="Test Investor",
            metadata={"source": "test"},
        )

    def create_info(self, user):
        class Context:
            pass

        class Info:
            pass

        context = Context()
        context.user = user

        info = Info()
        info.context = context

        return info

    def create_global_id(self, investor):
        return to_global_id(
            InvestorNode._meta.name,
            investor.pk,
        )

    def assert_requires_authentication(
        self,
        mutation,
        service_path,
        **input_data,
    ):
        class AnonymousUser:
            is_authenticated = False

        info = self.create_info(AnonymousUser())

        with patch(service_path) as service_method:
            with self.assertRaises(Exception) as raised:
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

    @patch("graphq.investors.mutations.InvestorService.update")
    def test_update_investor_delegates_to_service(self, update):
        user = self.create_user()
        investor = self.create_investor(
            email="target@example.com",
        )
        info = self.create_info(user)
        global_id = self.create_global_id(investor)

        update.return_value = investor

        result = UpdateInvestor.mutate_and_get_payload(
            None,
            info,
            id=global_id,
            display_name="Updated Investor",
            client_mutation_id="update-1",
        )

        self.assertIs(result.investor, investor)

        update.assert_called_once_with(
            investor=investor,
            actor=user,
            display_name="Updated Investor",
        )

        self.assertEqual(
            result.client_mutation_id,
            "update-1",
        )

    @patch("graphq.investors.mutations.InvestorService.update")
    def test_update_investor_requires_authentication(self, update):
        investor = self.create_investor()

        self.assert_requires_authentication(
            UpdateInvestor,
            "graphq.investors.mutations.InvestorService.update",
            id=self.create_global_id(investor),
            display_name="Updated Investor",
            client_mutation_id="update-2",
        )

        update.assert_not_called()

    @patch("graphq.investors.mutations.InvestorService.activate")
    def test_activate_investor_delegates_to_service(self, activate):
        user = self.create_user()
        investor = self.create_investor(
            email="activate@example.com",
        )
        info = self.create_info(user)

        activate.return_value = investor

        result = ActivateInvestor.mutate_and_get_payload(
            None,
            info,
            id=self.create_global_id(investor),
            client_mutation_id="activate-1",
        )

        self.assertIs(result.investor, investor)

        activate.assert_called_once_with(
            investor=investor,
            actor=user,
        )

        self.assertEqual(
            result.client_mutation_id,
            "activate-1",
        )

    @patch("graphq.investors.mutations.InvestorService.activate")
    def test_activate_investor_requires_authentication(self, activate):
        investor = self.create_investor()

        self.assert_requires_authentication(
            ActivateInvestor,
            "graphq.investors.mutations.InvestorService.activate",
            id=self.create_global_id(investor),
            client_mutation_id="activate-2",
        )

        activate.assert_not_called()

    @patch("graphq.investors.mutations.InvestorService.suspend")
    def test_suspend_investor_delegates_to_service(self, suspend):
        user = self.create_user()
        investor = self.create_investor(
            email="suspend@example.com",
        )
        info = self.create_info(user)

        suspend.return_value = investor

        result = SuspendInvestor.mutate_and_get_payload(
            None,
            info,
            id=self.create_global_id(investor),
            client_mutation_id="suspend-1",
        )

        self.assertIs(result.investor, investor)

        suspend.assert_called_once_with(
            investor=investor,
            actor=user,
        )

        self.assertEqual(
            result.client_mutation_id,
            "suspend-1",
        )

    @patch("graphq.investors.mutations.InvestorService.suspend")
    def test_suspend_investor_requires_authentication(self, suspend):
        investor = self.create_investor()

        self.assert_requires_authentication(
            SuspendInvestor,
            "graphq.investors.mutations.InvestorService.suspend",
            id=self.create_global_id(investor),
            client_mutation_id="suspend-2",
        )

        suspend.assert_not_called()

    @patch("graphq.investors.mutations.InvestorService.close")
    def test_close_investor_delegates_to_service(self, close):
        user = self.create_user()
        investor = self.create_investor(
            email="close@example.com",
        )
        info = self.create_info(user)

        close.return_value = investor

        result = CloseInvestor.mutate_and_get_payload(
            None,
            info,
            id=self.create_global_id(investor),
            client_mutation_id="close-1",
        )

        self.assertIs(result.investor, investor)

        close.assert_called_once_with(
            investor=investor,
            actor=user,
        )

        self.assertEqual(
            result.client_mutation_id,
            "close-1",
        )

    @patch("graphq.investors.mutations.InvestorService.close")
    def test_close_investor_requires_authentication(self, close):
        investor = self.create_investor()

        self.assert_requires_authentication(
            CloseInvestor,
            "graphq.investors.mutations.InvestorService.close",
            id=self.create_global_id(investor),
            client_mutation_id="close-2",
        )

        close.assert_not_called()
