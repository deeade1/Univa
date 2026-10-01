# apps/backend/graphq/banking/mutations/card.py

"""
GraphQL mutations for Banking card models.

Money movement
--------------

    authorizeTransaction   account -> SUSPENSE
    settleTransaction      SUSPENSE -> SETTLEMENT
    reverseAuthorization   SUSPENSE -> account
    requestPhysicalCard    account -> FEE

All delegated to banking.services.card_service.CardService.

Card PIN operations live on BankingSecurity (see
graphq/banking/mutations/security.py). VirtualCard no longer stores
a PIN.
"""

import logging
from decimal import Decimal

import graphene
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from graphene import (
    Boolean,
    Decimal as GrapheneDecimal,
    Field,
    ID,
    Int,
    String,
    relay,
)
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.cards import (
    CardBrand,
    CardTransaction,
    PhysicalCard,
    VirtualCard,
)
from banking.models.core import Account
from banking.services.card_service import CardService
from graphq.banking.types.card import (
    CardBrandNode,
    CardTransactionNode,
    PhysicalCardNode,
    VirtualCardNode,
)
from univa_jwt.decorators import login_required


logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _require_staff(user):
    if not user.is_staff:
        raise GraphQLError("Staff privileges required.")


def _get_model_by_global_id(global_id, model, model_name):
    if not global_id:
        raise GraphQLError(f"{model_name} ID is required.")
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{model_name} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {model_name} ID.") from exc


def _clean_message(exc):
    messages = getattr(exc, "messages", None)
    if messages:
        return str(messages[0])
    return str(exc)


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValidationError as exc:
        raise GraphQLError(_clean_message(exc)) from exc


# ============================================================================
# CARD BRAND MUTATIONS (staff)
# ============================================================================

class CreateCardBrandMutation(relay.ClientIDMutation):
    class Input:
        name = String(required=True)
        code = String(required=True)
        is_active = Boolean()

    card_brand = Field(CardBrandNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        if CardBrand.objects.filter(name=input["name"]).exists():
            raise GraphQLError(
                "Card brand with this name already exists."
            )
        if CardBrand.objects.filter(code=input["code"]).exists():
            raise GraphQLError(
                "Card brand with this code already exists."
            )

        try:
            card_brand = CardBrand.objects.create(
                name=input["name"],
                code=input["code"],
                is_active=input.get("is_active", True),
            )
        except ValidationError as exc:
            raise GraphQLError(_clean_message(exc)) from exc

        return cls(
            card_brand=card_brand,
            success=True,
            message="Card brand created successfully.",
        )


class UpdateCardBrandMutation(relay.ClientIDMutation):
    class Input:
        card_brand_id = ID(required=True)
        name = String()
        code = String()
        is_active = Boolean()

    card_brand = Field(CardBrandNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        card_brand = _get_model_by_global_id(
            input["card_brand_id"], CardBrand, "Card brand"
        )

        if input.get("name"):
            if (
                CardBrand.objects
                .filter(name=input["name"])
                .exclude(pk=card_brand.pk)
                .exists()
            ):
                raise GraphQLError(
                    "Card brand with this name already exists."
                )
            card_brand.name = input["name"]

        if input.get("code"):
            if (
                CardBrand.objects
                .filter(code=input["code"])
                .exclude(pk=card_brand.pk)
                .exists()
            ):
                raise GraphQLError(
                    "Card brand with this code already exists."
                )
            card_brand.code = input["code"]

        if input.get("is_active") is not None:
            card_brand.is_active = input["is_active"]

        card_brand.save()

        return cls(
            card_brand=card_brand,
            success=True,
            message="Card brand updated successfully.",
        )


class DeleteCardBrandMutation(relay.ClientIDMutation):
    class Input:
        card_brand_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        _require_staff(user)

        card_brand = _get_model_by_global_id(
            input["card_brand_id"], CardBrand, "Card brand"
        )

        if VirtualCard.objects.filter(card_brand=card_brand).exists():
            raise GraphQLError(
                "Cannot delete card brand with existing cards."
            )

        card_brand.delete()

        return cls(
            success=True,
            message="Card brand deleted successfully.",
        )


# ============================================================================
# VIRTUAL CARD MUTATIONS
# ============================================================================

class CreateVirtualCardMutation(relay.ClientIDMutation):
    """Issue a virtual card for the authenticated user."""

    class Input:
        account_id = ID(required=True)
        card_type = String(required=True)
        card_holder_name = String()
        daily_limit = GrapheneDecimal()
        monthly_limit = GrapheneDecimal()
        per_transaction_limit = GrapheneDecimal()

    virtual_card = Field(VirtualCardNode)
    success = Boolean()
    message = String()
    card_number = String()
    cvv = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )
        if account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        card = _wrap(
            CardService.issue_virtual_card,
            user=user,
            account=account,
            card_type=input["card_type"],
            card_holder_name=input.get("card_holder_name"),
            daily_limit=input.get("daily_limit"),
            monthly_limit=input.get("monthly_limit"),
            per_transaction_limit=input.get("per_transaction_limit"),
        )

        # Plaintext card number / CVV returned once at issuance
        plaintext_number = _wrap(CardService.decrypt_field, card.card_number)
        plaintext_cvv = _wrap(CardService.decrypt_field, card.cvv)

        return cls(
            virtual_card=card,
            success=True,
            message="Virtual card created successfully.",
            card_number=plaintext_number,
            cvv=plaintext_cvv,
        )


class UpdateVirtualCardMutation(relay.ClientIDMutation):
    """Update virtual card metadata (limits, freeze state)."""

    class Input:
        virtual_card_id = ID(required=True)
        card_holder_name = String()
        daily_limit = GrapheneDecimal()
        monthly_limit = GrapheneDecimal()
        per_transaction_limit = GrapheneDecimal()
        is_frozen = Boolean()
        is_lost = Boolean()
        is_stolen = Boolean()

    virtual_card = Field(VirtualCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["virtual_card_id"], VirtualCard, "Virtual card"
        )
        if card.user_id != user.pk:
            raise GraphQLError("You do not own this card.")

        if card.is_expired:
            raise GraphQLError("Cannot update an expired card.")

        if input.get("card_holder_name"):
            card.card_holder_name = input["card_holder_name"]

        if input.get("daily_limit"):
            new_daily = Decimal(str(input["daily_limit"]))
            if new_daily > card.monthly_limit:
                raise GraphQLError(
                    "Daily limit cannot exceed monthly limit."
                )
            card.daily_limit = new_daily

        if input.get("monthly_limit"):
            new_monthly = Decimal(str(input["monthly_limit"]))
            if card.daily_limit > new_monthly:
                raise GraphQLError(
                    "Daily limit cannot exceed monthly limit."
                )
            card.monthly_limit = new_monthly

        if input.get("per_transaction_limit"):
            new_per = Decimal(str(input["per_transaction_limit"]))
            if new_per > card.daily_limit:
                raise GraphQLError(
                    "Per-transaction limit cannot exceed daily limit."
                )
            card.per_transaction_limit = new_per

        if input.get("is_frozen") is not None:
            card.is_frozen = input["is_frozen"]
            card.status = "FROZEN" if input["is_frozen"] else "ACTIVE"

        if input.get("is_lost") is not None:
            card.is_lost = input["is_lost"]
            if input["is_lost"]:
                card.status = "BLOCKED"
                card.is_active = False

        if input.get("is_stolen") is not None:
            card.is_stolen = input["is_stolen"]
            if input["is_stolen"]:
                card.status = "BLOCKED"
                card.is_active = False

        card.save()

        return cls(
            virtual_card=card,
            success=True,
            message="Virtual card updated successfully.",
        )


class BlockVirtualCardMutation(relay.ClientIDMutation):
    class Input:
        virtual_card_id = ID(required=True)
        reason = String()

    virtual_card = Field(VirtualCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["virtual_card_id"], VirtualCard, "Virtual card"
        )
        if card.user_id != user.pk:
            raise GraphQLError("You do not own this card.")

        card.status = "BLOCKED"
        card.is_active = False
        card.save()

        return cls(
            virtual_card=card,
            success=True,
            message=(
                "Card blocked. Reason: "
                f"{input.get('reason', 'No reason provided')}"
            ),
        )


class UnblockVirtualCardMutation(relay.ClientIDMutation):
    class Input:
        virtual_card_id = ID(required=True)

    virtual_card = Field(VirtualCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["virtual_card_id"], VirtualCard, "Virtual card"
        )
        if card.user_id != user.pk:
            raise GraphQLError("You do not own this card.")

        if card.is_expired:
            raise GraphQLError("Cannot unblock an expired card.")

        card.status = "ACTIVE"
        card.is_active = True
        card.is_frozen = False
        card.save()

        return cls(
            virtual_card=card,
            success=True,
            message="Card unblocked successfully.",
        )


class CloseVirtualCardMutation(relay.ClientIDMutation):
    class Input:
        virtual_card_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["virtual_card_id"], VirtualCard, "Virtual card"
        )
        if card.user_id != user.pk:
            raise GraphQLError("You do not own this card.")

        if card.transactions.filter(status="PENDING").exists():
            raise GraphQLError(
                "Cannot close card with pending transactions."
            )

        card.status = "CLOSED"
        card.is_active = False
        card.save()

        return cls(
            success=True,
            message="Card closed successfully.",
        )


# ============================================================================
# CARD TRANSACTION MUTATIONS
# ============================================================================

class AuthorizeCardTransactionMutation(relay.ClientIDMutation):
    """
    Authorize a card transaction. Posts account -> SUSPENSE.
    """

    class Input:
        card_id = ID(required=True)
        account_id = ID(required=True)
        amount = GrapheneDecimal(required=True)
        currency = String()
        merchant_name = String(required=True)
        merchant_category_code = String(required=True)
        merchant_country = String(required=True)
        acquirer_id = String()

    card_transaction = Field(CardTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card = _get_model_by_global_id(
            input["card_id"], VirtualCard, "Card"
        )
        if card.user_id != user.pk:
            raise GraphQLError("You do not own this card.")

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )
        if account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        card_transaction = _wrap(
            CardService.authorize_transaction,
            card=card,
            account=account,
            amount=input["amount"],
            merchant_name=input["merchant_name"],
            merchant_category_code=input["merchant_category_code"],
            merchant_country=input.get("merchant_country", "NG"),
            acquirer_id=input.get("acquirer_id", "LOCAL"),
            currency=input.get("currency", "NGN"),
        )

        return cls(
            card_transaction=card_transaction,
            success=True,
            message="Transaction authorized successfully.",
        )


class SettleCardTransactionMutation(relay.ClientIDMutation):
    """Settle an authorized card transaction. Posts SUSPENSE -> SETTLEMENT."""

    class Input:
        auth_code = String(required=True)

    card_transaction = Field(CardTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card_transaction = _wrap(
            CardService.settle_transaction,
            auth_code=input["auth_code"],
        )

        if (
            card_transaction.user_id != user.pk
            and not user.is_staff
        ):
            raise GraphQLError(
                "You do not own this transaction."
            )

        return cls(
            card_transaction=card_transaction,
            success=True,
            message="Transaction settled successfully.",
        )


class ReverseCardAuthorizationMutation(relay.ClientIDMutation):
    """Reverse an authorization. Posts SUSPENSE -> account."""

    class Input:
        auth_code = String(required=True)
        reason = String()

    card_transaction = Field(CardTransactionNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        card_transaction = _wrap(
            CardService.reverse_authorization,
            auth_code=input["auth_code"],
            reason=input.get("reason", ""),
        )

        if (
            card_transaction.user_id != user.pk
            and not user.is_staff
        ):
            raise GraphQLError(
                "You do not own this transaction."
            )

        return cls(
            card_transaction=card_transaction,
            success=True,
            message="Authorization reversed successfully.",
        )


# ============================================================================
# PHYSICAL CARD MUTATIONS
# ============================================================================

class RequestPhysicalCardMutation(relay.ClientIDMutation):
    """
    Request a physical card for a virtual card.

    Posts account -> FEE for (card_fee + shipping_fee).
    """

    class Input:
        virtual_card_id = ID(required=True)
        account_id = ID(required=True)
        delivery_address = String(required=True)
        delivery_city = String(required=True)
        delivery_state = String(required=True)
        delivery_country = String()
        delivery_phone = String(required=True)
        shipping_method = String(required=True)
        card_fee = GrapheneDecimal(required=True)
        shipping_fee = GrapheneDecimal()

    physical_card = Field(PhysicalCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        virtual_card = _get_model_by_global_id(
            input["virtual_card_id"], VirtualCard, "Virtual card"
        )
        if virtual_card.user_id != user.pk:
            raise GraphQLError("You do not own this card.")

        account = _get_model_by_global_id(
            input["account_id"], Account, "Account"
        )
        if account.user_id != user.pk:
            raise GraphQLError("You do not own this account.")

        physical_card = _wrap(
            CardService.request_physical_card,
            user=user,
            virtual_card=virtual_card,
            account=account,
            delivery_address=input["delivery_address"],
            delivery_city=input["delivery_city"],
            delivery_state=input["delivery_state"],
            delivery_country=input.get("delivery_country", "NG"),
            delivery_phone=input["delivery_phone"],
            shipping_method=input["shipping_method"],
            card_fee=input["card_fee"],
            shipping_fee=input.get("shipping_fee"),
        )

        return cls(
            physical_card=physical_card,
            success=True,
            message="Physical card requested successfully.",
        )


class UpdatePhysicalCardMutation(relay.ClientIDMutation):
    class Input:
        physical_card_id = ID(required=True)
        delivery_status = String()
        tracking_number = String()
        shipping_method = String()

    physical_card = Field(PhysicalCardNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        physical_card = _get_model_by_global_id(
            input["physical_card_id"], PhysicalCard, "Physical card"
        )
        if physical_card.user_id != user.pk and not user.is_staff:
            raise GraphQLError(
                "You do not own this physical card request."
            )

        if input.get("delivery_status"):
            valid_statuses = [
                choice[0] for choice in PhysicalCard.DELIVERY_STATUS
            ]
            if input["delivery_status"] not in valid_statuses:
                raise GraphQLError("Invalid delivery status.")
            physical_card.delivery_status = input["delivery_status"]

            if input["delivery_status"] == "SHIPPED":
                physical_card.shipped_at = timezone.now()
            elif input["delivery_status"] == "DELIVERED":
                physical_card.delivered_at = timezone.now()

        if input.get("tracking_number") is not None:
            physical_card.tracking_number = input["tracking_number"]

        if input.get("shipping_method") is not None:
            physical_card.shipping_method = input["shipping_method"]

        physical_card.save()

        return cls(
            physical_card=physical_card,
            success=True,
            message="Physical card updated successfully.",
        )


class CancelPhysicalCardMutation(relay.ClientIDMutation):
    class Input:
        physical_card_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)

        physical_card = _get_model_by_global_id(
            input["physical_card_id"], PhysicalCard, "Physical card"
        )
        if physical_card.user_id != user.pk and not user.is_staff:
            raise GraphQLError(
                "You do not own this physical card request."
            )

        if physical_card.delivery_status in ["SHIPPED", "DELIVERED"]:
            raise GraphQLError(
                "Cannot cancel a card that has already been shipped."
            )

        physical_card.delivery_status = "CANCELLED"
        physical_card.save()

        return cls(
            success=True,
            message="Physical card request cancelled.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class CardMutations(graphene.ObjectType):
    # Card Brand (staff)
    create_card_brand = CreateCardBrandMutation.Field()
    update_card_brand = UpdateCardBrandMutation.Field()
    delete_card_brand = DeleteCardBrandMutation.Field()

    # Virtual Card
    create_virtual_card = CreateVirtualCardMutation.Field()
    update_virtual_card = UpdateVirtualCardMutation.Field()
    block_virtual_card = BlockVirtualCardMutation.Field()
    unblock_virtual_card = UnblockVirtualCardMutation.Field()
    close_virtual_card = CloseVirtualCardMutation.Field()

    # Card Transaction (money movement)
    authorize_card_transaction = AuthorizeCardTransactionMutation.Field()
    settle_card_transaction = SettleCardTransactionMutation.Field()
    reverse_card_authorization = ReverseCardAuthorizationMutation.Field()

    # Physical Card
    request_physical_card = RequestPhysicalCardMutation.Field()
    update_physical_card = UpdatePhysicalCardMutation.Field()
    cancel_physical_card = CancelPhysicalCardMutation.Field()


__all__ = [
    "CreateCardBrandMutation",
    "UpdateCardBrandMutation",
    "DeleteCardBrandMutation",
    "CreateVirtualCardMutation",
    "UpdateVirtualCardMutation",
    "BlockVirtualCardMutation",
    "UnblockVirtualCardMutation",
    "CloseVirtualCardMutation",
    "AuthorizeCardTransactionMutation",
    "SettleCardTransactionMutation",
    "ReverseCardAuthorizationMutation",
    "RequestPhysicalCardMutation",
    "UpdatePhysicalCardMutation",
    "CancelPhysicalCardMutation",
    "CardMutations",
]