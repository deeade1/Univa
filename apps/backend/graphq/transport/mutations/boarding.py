# apps/backend/graphq/transport/mutations/boarding_ticket.py
"""
BoardingTicket mutations.

Model facts that shape these mutations:
    - `trip` FK targets `Trip` (a proxy of ServiceRequest).
    - `user` FK targets the passenger. A ticket always belongs to a user.
    - `booking` FK is optional.
    - `redeem()` / `cancel()` are state-machine helpers on the model;
      they must be used instead of raw field writes.
    - `generate_ticket_number()` produces a unique ticket number; only
      call it when the caller didn't supply one.
    - `generate_qr()` writes a QR PNG and stores `qr_code_data`.

Ownership:
    - Owner (the user the ticket belongs to) or staff may cancel.
    - Staff may redeem (check-in is a staff action) — a customer
      redeeming their own ticket is allowed only if `ALLOW_SELF_REDEEM`
      is True; default is False because redemption usually happens at
      the gate.
    - Deletion is staff-only.
"""

import logging

import graphene
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.boarding import BoardingTicketNode
from graphq.transport.types.trip import TripNode
from graphq.accounts.types.user import UserNode

from transport.models.rides.boarding import BoardingTicket
from transport.models.rides.trip import Trip


logger = logging.getLogger(__name__)

# Whether a passenger may redeem their own ticket. Set to True only
# for self-service check-in scenarios.
ALLOW_SELF_REDEEM = False

_VALID_TICKET_TYPES = {"standard", "premium", "vip", "discount", "promotional"}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_trip(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid trip_id.")
    try:
        return Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        raise GraphQLError("Trip not found.")


def _resolve_user(global_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid user_id.")
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise GraphQLError("User not found.")


def _resolve_ticket(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid boarding_ticket_id.")
    qs = BoardingTicket.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except BoardingTicket.DoesNotExist:
        raise GraphQLError("Boarding ticket not found.")


def _assert_can_manage(ticket, user):
    """Owner or staff may manage the ticket."""
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    if ticket.user_id == user.pk:
        return
    raise GraphQLError("Not authorized to manage this ticket.")


def _assert_can_redeem(user):
    """Only staff can redeem unless self-redemption is enabled."""
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff or ALLOW_SELF_REDEEM:
        return
    raise GraphQLError("Only staff may redeem tickets.")


def _validate_ticket_type(value):
    if value is None:
        return
    if value not in _VALID_TICKET_TYPES:
        raise GraphQLError(
            f"ticket_type must be one of: {', '.join(sorted(_VALID_TICKET_TYPES))}."
        )


# =============================================================================
# Create
# =============================================================================

class CreateBoardingTicket(relay.ClientIDMutation):
    """
    Create a BoardingTicket.

    `user` defaults to the caller. Staff may set `user_id` for
    on-behalf creation (e.g. box-office sales). `ticket_number` is
    auto-generated when not supplied.
    """

    class Input:
        trip_id = graphene.ID(required=True)

        user_id = graphene.ID()             # staff-only override
        booking_id = graphene.ID()          # optional

        seat_number = graphene.String()
        ticket_number = graphene.String()   # auto-generated if omitted
        ticket_type = graphene.String(default_value="standard")

        # Whether to generate a QR image immediately.
        generate_qr = graphene.Boolean(default_value=False)

    boarding_ticket = graphene.Field(BoardingTicketNode)
    trip = graphene.Field(TripNode)
    user = graphene.Field(UserNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, trip_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        trip = _resolve_trip(trip_id)

        # Resolve user (self by default).
        if input.get("user_id"):
            if not me.is_staff:
                raise GraphQLError("Only staff may create tickets for other users.")
            ticket_user = _resolve_user(input["user_id"])
        else:
            ticket_user = me

        # Resolve booking (optional).
        booking = None
        if input.get("booking_id"):
            from transport.models.booking.booking import Booking
            try:
                _, booking_pk = from_global_id(input["booking_id"])
            except Exception:
                raise GraphQLError("Invalid booking_id.")
            try:
                booking = Booking.objects.get(pk=booking_pk)
            except Booking.DoesNotExist:
                raise GraphQLError("Booking not found.")
            if booking.service_request_id != trip.pk:
                raise GraphQLError("Booking does not belong to this trip.")
            if not me.is_staff and booking.user_id != me.pk:
                raise GraphQLError("Not authorized to use this booking.")

        _validate_ticket_type(input.get("ticket_type"))

        # Duplicate check mirrors the model's unique constraint.
        if BoardingTicket.objects.filter(
            trip=trip, user=ticket_user, booking=booking
        ).exists():
            raise GraphQLError(
                "A ticket for this trip, user, and booking already exists."
            )

        payload = {
            "trip": trip,
            "user": ticket_user,
            "booking": booking,
            "seat_number": input.get("seat_number"),
            "ticket_number": input.get("ticket_number"),
            "ticket_type": input.get("ticket_type") or "standard",
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            ticket = BoardingTicket.objects.create(**payload)
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Auto-generate ticket_number if missing.
        if not ticket.ticket_number:
            try:
                ticket.generate_ticket_number()
                ticket.save(update_fields=["ticket_number", "updated_at"])
            except Exception as exc:
                logger.warning("Ticket number generation failed: %s", exc)

        # Optional QR generation.
        if input.get("generate_qr"):
            try:
                ticket.generate_qr()
            except Exception as exc:
                logger.warning("QR generation failed: %s", exc)

        return cls(
            boarding_ticket=ticket,
            trip=trip,
            user=ticket_user,
            success=True,
            message="Boarding ticket created.",
        )


# =============================================================================
# Update (metadata only)
# =============================================================================

class UpdateBoardingTicket(relay.ClientIDMutation):
    """
    Update a ticket's mutable metadata.

    `redeemed` / `cancelled` are NOT editable here — use `RedeemBoardingTicket`
    and `CancelBoardingTicket`, which enforce the state machine.
    """

    class Input:
        boarding_ticket_id = graphene.ID(required=True)

        seat_number = graphene.String()
        ticket_number = graphene.String()
        ticket_type = graphene.String()

        regenerate_qr = graphene.Boolean(default_value=False)

    boarding_ticket = graphene.Field(BoardingTicketNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, boarding_ticket_id, **input):
        me = info.context.user
        ticket = _resolve_ticket(boarding_ticket_id, lock=True)
        _assert_can_manage(ticket, me)

        if ticket.cancelled or ticket.redeemed:
            raise GraphQLError(
                "Cannot edit a ticket that has been redeemed or cancelled."
            )

        if "ticket_type" in input and input["ticket_type"] is not None:
            _validate_ticket_type(input["ticket_type"])

        update_fields = []

        for field in ("seat_number", "ticket_number", "ticket_type"):
            if field in input and input[field] is not None:
                # Only staff may reassign ticket_number explicitly —
                # it's an identifier and normally auto-generated once.
                if field == "ticket_number" and not me.is_staff:
                    if ticket.ticket_number and input[field] != ticket.ticket_number:
                        raise GraphQLError(
                            "Only staff may change an existing ticket number."
                        )
                setattr(ticket, field, input[field])
                update_fields.append(field)

        if not update_fields and not input.get("regenerate_qr"):
            return cls(
                boarding_ticket=ticket,
                success=True,
                message="Nothing to update.",
            )

        if update_fields:
            try:
                ticket.full_clean()
            except ValidationError as exc:
                raise GraphQLError(f"Validation failed: {exc.message_dict}")
            ticket.save(update_fields=sorted(set(update_fields + ["updated_at"])))

        if input.get("regenerate_qr"):
            try:
                ticket.generate_qr()
            except Exception as exc:
                raise GraphQLError(f"QR generation failed: {exc}")

        return cls(
            boarding_ticket=ticket,
            success=True,
            message="Boarding ticket updated.",
        )


# =============================================================================
# Redeem / Cancel
# =============================================================================

class RedeemBoardingTicket(relay.ClientIDMutation):
    """
    Redeem (check-in) a ticket.

    Uses the model's `redeem()` helper, which sets `redeemed`,
    `redeemed_at`, `used_at`, and optionally `checked_in_by`.
    Staff-only unless `ALLOW_SELF_REDEEM` is enabled.
    """

    class Input:
        boarding_ticket_id = graphene.ID(required=True)

    boarding_ticket = graphene.Field(BoardingTicketNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, boarding_ticket_id):
        me = info.context.user
        _assert_can_redeem(me)

        ticket = _resolve_ticket(boarding_ticket_id, lock=True)

        # Staff can redeem for anyone; self-redeemers are limited to their own.
        if not me.is_staff and ticket.user_id != me.pk:
            raise GraphQLError("Not authorized to redeem this ticket.")

        try:
            ticket.redeem(staff_user=me if me.is_staff else None)
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            boarding_ticket=ticket,
            success=True,
            message="Ticket redeemed.",
        )


class CancelBoardingTicket(relay.ClientIDMutation):
    """
    Cancel a ticket.

    Uses the model's `cancel()` helper, which sets `cancelled` and
    `cancelled_at`. Owner or staff.
    """

    class Input:
        boarding_ticket_id = graphene.ID(required=True)

    boarding_ticket = graphene.Field(BoardingTicketNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, boarding_ticket_id):
        me = info.context.user
        ticket = _resolve_ticket(boarding_ticket_id, lock=True)
        _assert_can_manage(ticket, me)

        try:
            ticket.cancel()
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            boarding_ticket=ticket,
            success=True,
            message="Ticket cancelled.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteBoardingTicket(relay.ClientIDMutation):
    """
    Delete a BoardingTicket.

    Staff-only. Tickets are audit records — a passenger should not be
    able to erase a ticket. Use `CancelBoardingTicket` to invalidate one.
    """

    class Input:
        boarding_ticket_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, boarding_ticket_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete boarding tickets.")

        ticket = _resolve_ticket(boarding_ticket_id, lock=True)

        # Optional: refuse deleting a ticket that's been used, since
        # that's an audit trail of a completed journey.
        if ticket.redeemed:
            raise GraphQLError(
                "Cannot delete a redeemed ticket. Cancel it instead."
            )

        ticket.delete()
        return cls(success=True, message="Boarding ticket deleted.")


# =============================================================================
# Registration
# =============================================================================

class BoardingTicketMutations(graphene.ObjectType):
    create_boarding_ticket = CreateBoardingTicket.Field()
    update_boarding_ticket = UpdateBoardingTicket.Field()
    redeem_boarding_ticket = RedeemBoardingTicket.Field()
    cancel_boarding_ticket = CancelBoardingTicket.Field()
    delete_boarding_ticket = DeleteBoardingTicket.Field()