# apps/backend/graphq/transport/mutations/booking.py
"""
Booking mutations.

Model facts that shape these mutations:
    - `service_request` and `user` are both required FKs.
    - `booked_at` is auto_now_add; there is no user-facing "booking time".
    - `status` transitions have helpers on the model: `confirm()`,
      `cancel()`, `complete()`. `save()` auto-fills the matching
      `*_at` timestamp when status changes.
    - `clean()` refuses CONFIRMED status without an assigned provider.

Ownership:
    - Owner (the user the booking belongs to) or the assigned provider
      may confirm / complete.
    - Owner or staff may cancel.
    - Deletion is staff-only.
"""

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from graphene import relay
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.booking import BookingNode
from graphq.transport.types.trip import TripNode
from graphq.accounts.types.user import UserNode

from transport.models.rides.booking import Booking
from transport.models.core.service_request import ServiceRequest


User = get_user_model()

_ALLOWED_STATUSES = {choice[0] for choice in Booking.Status.choices}
_TERMINAL_STATUSES = {Booking.Status.CANCELLED, Booking.Status.COMPLETED}


# =============================================================================
# Helpers
# =============================================================================

def _resolve_booking(global_id, *, lock=False):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid booking_id.")
    qs = Booking.objects.all()
    if lock:
        qs = qs.select_for_update()
    try:
        return qs.get(pk=pk)
    except Booking.DoesNotExist:
        raise GraphQLError("Booking not found.")


def _resolve_service_request(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid service_request_id.")
    try:
        return ServiceRequest.objects.get(pk=pk)
    except ServiceRequest.DoesNotExist:
        raise GraphQLError("Service request not found.")


def _resolve_user(global_id):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError("Invalid user_id.")
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise GraphQLError("User not found.")


def _assert_can_manage(booking, user, *, owner_only=False):
    """
    Owner-only when `owner_only=True` (for actions the provider shouldn't
    perform, e.g. cancel). Otherwise owner, assigned provider, or staff.
    """
    if not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    if user.is_staff:
        return
    if booking.user_id == user.pk:
        return
    if owner_only:
        raise GraphQLError("Not authorized for this booking.")

    provider = getattr(user, "service_provider", None)
    if (
        provider is not None
        and booking.service_request.provider_id == provider.pk
    ):
        return
    raise GraphQLError("Not authorized for this booking.")


# =============================================================================
# Create
# =============================================================================

class CreateBooking(relay.ClientIDMutation):
    """
    Create a Booking.

    `user` defaults to the caller; staff may pass `user_id`. The
    booking always starts in `PENDING`.
    """

    class Input:
        service_request_id = graphene.ID(required=True)
        user_id = graphene.ID()  # staff-only override

    booking = graphene.Field(BookingNode)
    user = graphene.Field(UserNode)
    trip = graphene.Field(TripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, service_request_id, user_id=None):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        service_request = _resolve_service_request(service_request_id)

        booking_user = me
        if user_id:
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may create bookings for other users."
                )
            booking_user = _resolve_user(user_id)

        # Duplicate guard (not enforced by the model, but bookings for
        # the same user on the same request are almost always a bug).
        if Booking.objects.filter(
            service_request=service_request,
            user=booking_user,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        ).exists():
            raise GraphQLError(
                "An active booking already exists for this user and request."
            )

        try:
            booking = Booking.objects.create(
                service_request=service_request,
                user=booking_user,
                status=Booking.Status.PENDING,
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")
        except IntegrityError as exc:
            raise GraphQLError(f"Integrity error: {exc}")

        return cls(
            booking=booking,
            user=booking_user,
            trip=service_request,
            success=True,
            message="Booking created.",
        )


# =============================================================================
# Update
# =============================================================================

class UpdateBooking(relay.ClientIDMutation):
    """
    Update a booking's mutable metadata.

    Only `service_request` can be reassigned (staff-only — reassigning
    is effectively creating a new booking in spirit). Status changes
    go through dedicated mutations so the lifecycle timestamps and
    state-machine rules are respected.
    """

    class Input:
        booking_id = graphene.ID(required=True)
        service_request_id = graphene.ID()  # staff-only

    booking = graphene.Field(BookingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, booking_id, service_request_id=None):
        me = info.context.user
        booking = _resolve_booking(booking_id, lock=True)
        _assert_can_manage(booking, me)

        if booking.status in _TERMINAL_STATUSES:
            raise GraphQLError(
                f"Cannot update a booking in terminal state "
                f"'{booking.status}'."
            )

        if service_request_id:
            if not me.is_staff:
                raise GraphQLError(
                    "Only staff may reassign a booking to another request."
                )
            booking.service_request = _resolve_service_request(service_request_id)

        try:
            booking.full_clean()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        booking.save()
        return cls(
            booking=booking,
            success=True,
            message="Booking updated.",
        )


# =============================================================================
# Status transitions
# =============================================================================

class ConfirmBooking(relay.ClientIDMutation):
    """
    Confirm a booking.

    Requires an assigned provider on the ServiceRequest — the model's
    `clean()` raises otherwise. Owner or provider or staff.
    """

    class Input:
        booking_id = graphene.ID(required=True)

    booking = graphene.Field(BookingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, booking_id):
        me = info.context.user
        booking = _resolve_booking(booking_id, lock=True)
        _assert_can_manage(booking, me)

        if booking.status == Booking.Status.CANCELLED:
            raise GraphQLError("Cannot confirm a cancelled booking.")
        if booking.status == Booking.Status.COMPLETED:
            raise GraphQLError("Booking is already completed.")
        if booking.status == Booking.Status.CONFIRMED:
            return cls(
                booking=booking,
                success=True,
                message="Booking is already confirmed.",
            )

        try:
            booking.confirm()
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            booking=booking,
            success=True,
            message="Booking confirmed.",
        )


class CancelBooking(relay.ClientIDMutation):
    """Cancel a booking. Owner or staff."""

    class Input:
        booking_id = graphene.ID(required=True)

    booking = graphene.Field(BookingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, booking_id):
        me = info.context.user
        booking = _resolve_booking(booking_id, lock=True)
        _assert_can_manage(booking, me, owner_only=True)

        if booking.status == Booking.Status.CANCELLED:
            return cls(
                booking=booking,
                success=True,
                message="Booking is already cancelled.",
            )
        if booking.status == Booking.Status.COMPLETED:
            raise GraphQLError("Cannot cancel a completed booking.")

        try:
            booking.cancel()
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            booking=booking,
            success=True,
            message="Booking cancelled.",
        )


class CompleteBooking(relay.ClientIDMutation):
    """
    Mark a booking as completed.

    Provider or staff. `ServiceRequest` must be COMPLETED — the booking
    lifecycle should track the request lifecycle.
    """

    class Input:
        booking_id = graphene.ID(required=True)

    booking = graphene.Field(BookingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, booking_id):
        me = info.context.user
        booking = _resolve_booking(booking_id, lock=True)
        _assert_can_manage(booking, me)

        if booking.status == Booking.Status.CANCELLED:
            raise GraphQLError("Cannot complete a cancelled booking.")
        if booking.status == Booking.Status.COMPLETED:
            return cls(
                booking=booking,
                success=True,
                message="Booking is already completed.",
            )

        # The service request should already be complete.
        request_status = booking.service_request.status
        if request_status not in (
            ServiceRequest.Status.COMPLETED,
        ) and not me.is_staff:
            raise GraphQLError(
                "Cannot complete a booking before its service request "
                "is completed."
            )

        try:
            booking.complete()
        except ValidationError as exc:
            raise GraphQLError(str(exc))

        return cls(
            booking=booking,
            success=True,
            message="Booking completed.",
        )


# =============================================================================
# Delete
# =============================================================================

class DeleteBooking(relay.ClientIDMutation):
    """
    Delete a Booking.

    Staff-only. Bookings are transactional records — cancel rather
    than delete. Deleting is reserved for cleanup of erroneous rows
    (duplicates, test data).
    """

    class Input:
        booking_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, booking_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not me.is_staff:
            raise GraphQLError("Only staff may delete bookings.")

        booking = _resolve_booking(booking_id, lock=True)

        # Refuse to delete a completed booking — that's an audit trail.
        if booking.status == Booking.Status.COMPLETED:
            raise GraphQLError(
                "Cannot delete a completed booking. It is part of the "
                "audit trail."
            )

        booking.delete()
        return cls(success=True, message="Booking deleted.")


# =============================================================================
# Registration
# =============================================================================

class BookingMutations(graphene.ObjectType):
    create_booking = CreateBooking.Field()
    update_booking = UpdateBooking.Field()
    confirm_booking = ConfirmBooking.Field()
    cancel_booking = CancelBooking.Field()
    complete_booking = CompleteBooking.Field()
    delete_booking = DeleteBooking.Field()