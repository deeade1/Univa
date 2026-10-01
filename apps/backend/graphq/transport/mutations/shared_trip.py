# apps/backend/graphq/transport/mutations/shared_trip.py
"""
SharedTrip, WaitlistEntry, and UserPreference mutations.

SharedTrip is a proxy over ServiceRequest. All shared-specific state
lives in the `shared_trip_data` JSON field, exposed via properties with
setters. There is no `objects.create(available_seats=...)` — the setter
writes to `_shared_data`, and `save()` re-serializes it.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.shared_trip import (
    SharedTripNode,
    WaitlistEntryNode,
    UserPreferenceNode,
)

from transport.models.rides.shared_trip import (
    SharedTrip,
    WaitlistEntry,
    UserPreference,
)
from transport.models.core.service_request import ServiceRequest


# =============================================================================
# SharedTrip
# =============================================================================

class CreateSharedTrip(relay.ClientIDMutation):
    """
    Create a SharedTrip.

    The underlying row is a ServiceRequest with service_type='shared'.
    `pickup_location` / `dropoff_location` are FKs to StopPoint, so the
    client sends lat/lng and we resolve or create a StopPoint.
    """

    class Input:
        pickup_lat = graphene.Float(required=True)
        pickup_lng = graphene.Float(required=True)
        pickup_address = graphene.String()

        dropoff_lat = graphene.Float()
        dropoff_lng = graphene.Float()
        dropoff_address = graphene.String()

        available_seats = graphene.Int(required=True)
        day_time = graphene.String(required=True)   # 'day' | 'night'

        scheduled_at = graphene.DateTime()
        total_fare = graphene.Decimal()

        luggage_capacity_kg = graphene.Int()
        luggage_price_per_kg = graphene.Decimal()

        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        special_requests = graphene.String()
        metadata = graphene.JSONString()

    shared_trip = graphene.Field(SharedTripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        # Validate enum inputs against the model's TextChoices.
        day_time = input["day_time"]
        if day_time not in dict(SharedTrip.DayTime.choices):
            raise GraphQLError(
                f"day_time must be one of: "
                f"{', '.join(dict(SharedTrip.DayTime.choices).keys())}."
            )

        available_seats = input["available_seats"]
        if available_seats < 1:
            raise GraphQLError("available_seats must be at least 1.")

        # Resolve StopPoints
        from graphq.transport.mutations.service_request import (
            _resolve_or_create_stop_point,
        )

        pickup_stop = _resolve_or_create_stop_point(
            input["pickup_lat"],
            input["pickup_lng"],
            address=input.get("pickup_address") or "",
            label="pickup",
        )

        dropoff_stop = None
        if (
            input.get("dropoff_lat") is not None
            and input.get("dropoff_lng") is not None
        ):
            dropoff_stop = _resolve_or_create_stop_point(
                input["dropoff_lat"],
                input["dropoff_lng"],
                address=input.get("dropoff_address") or "",
                label="dropoff",
            )

        # Base ServiceRequest payload
        payload = {
            "customer": user,
            "service_type": ServiceRequest.ServiceType.SHARED,
            "status": (
                ServiceRequest.Status.SCHEDULED
                if input.get("scheduled_at")
                else ServiceRequest.Status.REQUESTED
            ),
            "pickup_location": pickup_stop,
            "dropoff_location": dropoff_stop,
            "scheduled_at": input.get("scheduled_at"),
            "total_fare": input.get("total_fare"),
            "luggage_capacity_kg": input.get("luggage_capacity_kg") or 0,
            "luggage_price_per_kg": input.get("luggage_price_per_kg"),
            "emergency_contact_name": input.get("emergency_contact_name") or "",
            "emergency_contact_phone": input.get("emergency_contact_phone") or "",
            "metadata": input.get("metadata") or {},
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        # Initial shared_trip_data
        payload["shared_trip_data"] = {
            "available_seats": available_seats,
            "day_time": day_time,
            "shared_status": SharedTrip.SharedStatus.AVAILABLE,
            "special_requests": input.get("special_requests") or "",
        }

        try:
            # Creating via SharedTrip (proxy) gives us the subclass instance
            # so properties work without re-fetching.
            trip = SharedTrip.objects.create(**payload)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Sync _shared_data so the response reflects what we just wrote.
        trip._shared_data = dict(trip.shared_trip_data or {})

        return cls(
            shared_trip=trip,
            success=True,
            message="Shared trip created.",
        )


class UpdateSharedTrip(relay.ClientIDMutation):
    """
    Update mutable fields on a SharedTrip.

    Ownership: the customer, or staff.
    Terminal statuses reject edits by non-staff.
    """

    class Input:
        shared_trip_id = graphene.ID(required=True)

        available_seats = graphene.Int()
        day_time = graphene.String()          # 'day' | 'night'
        shared_status = graphene.String()     # 'available' | 'full' | 'departed' | 'completed'

        scheduled_at = graphene.DateTime()
        total_fare = graphene.Decimal()

        luggage_capacity_kg = graphene.Int()
        luggage_price_per_kg = graphene.Decimal()

        emergency_contact_name = graphene.String()
        emergency_contact_phone = graphene.String()

        special_requests = graphene.String()
        metadata = graphene.JSONString()

    shared_trip = graphene.Field(SharedTripNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, shared_trip_id, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(shared_trip_id)
        except Exception:
            raise GraphQLError("Invalid shared_trip_id.")

        try:
            trip = SharedTrip.objects.select_for_update().get(pk=pk)
        except SharedTrip.DoesNotExist:
            raise GraphQLError("Shared trip not found.")

        if trip.customer_id != user.pk and not user.is_staff:
            raise GraphQLError("Not authorized to update this shared trip.")

        if trip.status in {
            ServiceRequest.Status.COMPLETED,
            ServiceRequest.Status.CANCELLED,
        } and not user.is_staff:
            raise GraphQLError(
                f"Cannot update a trip in terminal state '{trip.status}'."
            )

        # Ensure _shared_data reflects current persisted state.
        trip._shared_data = dict(trip.shared_trip_data or {})

        update_fields = []

        # -------- Scalar fields --------
        scalar_map = {
            "scheduled_at": "scheduled_at",
            "total_fare": "total_fare",
            "luggage_capacity_kg": "luggage_capacity_kg",
            "luggage_price_per_kg": "luggage_price_per_kg",
            "emergency_contact_name": "emergency_contact_name",
            "emergency_contact_phone": "emergency_contact_phone",
        }
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                setattr(trip, model_field, input[input_key])
                update_fields.append(model_field)

        # -------- metadata merge --------
        if input.get("metadata") is not None:
            if not isinstance(input["metadata"], dict):
                raise GraphQLError("metadata must be an object.")
            trip.metadata = {**(trip.metadata or {}), **input["metadata"]}
            update_fields.append("metadata")

        # -------- shared_trip_data via property setters --------
        shared_dirty = False

        if "available_seats" in input and input["available_seats"] is not None:
            seats = input["available_seats"]
            if seats < 0:
                raise GraphQLError("available_seats cannot be negative.")
            trip.shared_available_seats = seats
            shared_dirty = True
            # Flip availability when seats hit zero.
            if seats == 0:
                trip.shared_status = SharedTrip.SharedStatus.FULL

        if "day_time" in input and input["day_time"] is not None:
            if input["day_time"] not in dict(SharedTrip.DayTime.choices):
                raise GraphQLError(
                    f"day_time must be one of: "
                    f"{', '.join(dict(SharedTrip.DayTime.choices).keys())}."
                )
            trip.shared_day_time = input["day_time"]
            shared_dirty = True

        if "shared_status" in input and input["shared_status"] is not None:
            if input["shared_status"] not in dict(SharedTrip.SharedStatus.choices):
                raise GraphQLError(
                    f"shared_status must be one of: "
                    f"{', '.join(dict(SharedTrip.SharedStatus.choices).keys())}."
                )
            trip.shared_status = input["shared_status"]
            shared_dirty = True

        if "special_requests" in input and input["special_requests"] is not None:
            trip._shared_data["special_requests"] = input["special_requests"]
            shared_dirty = True

        if shared_dirty:
            # The save() override re-serializes _shared_data into
            # shared_trip_data — no need to add it to update_fields.
            update_fields.append("shared_trip_data")

        if not update_fields:
            return cls(
                shared_trip=trip,
                success=True,
                message="Nothing to update.",
            )

        # Bump updated_at for partial saves.
        update_fields = sorted(set(update_fields + ["updated_at"]))

        try:
            trip.save(update_fields=update_fields)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            shared_trip=trip,
            success=True,
            message="Shared trip updated.",
        )


class DeleteSharedTrip(relay.ClientIDMutation):
    """
    Delete a SharedTrip.

    Refuses while the trip has active waitlist entries or confirmed
    bookings — cancel first, then delete.
    """

    class Input:
        shared_trip_id = graphene.ID(required=True)
        force = graphene.Boolean(default_value=False)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, shared_trip_id, force=False):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(shared_trip_id)
        except Exception:
            raise GraphQLError("Invalid shared_trip_id.")

        try:
            trip = SharedTrip.objects.select_for_update().get(pk=pk)
        except SharedTrip.DoesNotExist:
            raise GraphQLError("Shared trip not found.")

        if trip.customer_id != user.pk and not user.is_staff:
            raise GraphQLError("Not authorized to delete this shared trip.")

        # Safety: block deleting active trips unless staff forces it.
        active_statuses = {
            ServiceRequest.Status.REQUESTED,
            ServiceRequest.Status.ACCEPTED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.SCHEDULED,
            ServiceRequest.Status.DEPARTED,
            ServiceRequest.Status.IN_TRANSIT,
        }
        if trip.status in active_statuses and not (user.is_staff and force):
            raise GraphQLError(
                "Cannot delete an active shared trip. "
                "Cancel it first, or use force=true as staff."
            )

        # Check for active waitlist entries.
        active_waitlist = WaitlistEntry.objects.filter(
            shared_trip=trip,
            expired=False,
        ).exists()
        if active_waitlist and not (user.is_staff and force):
            raise GraphQLError(
                "Cannot delete a shared trip with active waitlist entries."
            )

        try:
            trip.delete()
        except Exception as exc:
            raise GraphQLError(
                f"Delete blocked — trip has related records: {exc}"
            )

        return cls(success=True, message="Shared trip deleted.")


# =============================================================================
# WaitlistEntry
# =============================================================================

class JoinWaitlist(relay.ClientIDMutation):
    """
    Join the waitlist for a shared trip.

    The model auto-assigns `position` on save, so we never pass it.
    Uses get_or_create to be idempotent — a user who is already on the
    waitlist just gets their existing entry back.
    """

    class Input:
        shared_trip_id = graphene.ID(required=True)
        preferred_seats = graphene.List(graphene.Int)
        special_requests = graphene.String()

    waitlist_entry = graphene.Field(WaitlistEntryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        shared_trip_id,
        preferred_seats=None,
        special_requests=None,
    ):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(shared_trip_id)
        except Exception:
            raise GraphQLError("Invalid shared_trip_id.")

        try:
            trip = SharedTrip.objects.get(pk=pk)
        except SharedTrip.DoesNotExist:
            raise GraphQLError("Shared trip not found.")

        if trip.shared_status == SharedTrip.SharedStatus.COMPLETED:
            raise GraphQLError("Cannot join the waitlist of a completed trip.")

        # Idempotent: existing active entry is returned unchanged.
        existing = WaitlistEntry.objects.filter(
            shared_trip=trip,
            user=user,
            expired=False,
        ).first()
        if existing:
            return cls(
                waitlist_entry=existing,
                success=True,
                message="You are already on the waitlist.",
            )

        try:
            entry = WaitlistEntry.objects.create(
                shared_trip=trip,
                user=user,
                preferred_seats=preferred_seats or [],
                special_requests=special_requests or "",
                expired=False,
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            waitlist_entry=entry,
            success=True,
            message=f"Added to waitlist at position {entry.position}.",
        )


class UpdateWaitlistEntry(relay.ClientIDMutation):
    """
    Update a waitlist entry.

    Only the caller's own entry can be updated, and only the
    client-settable fields (`preferred_seats`, `special_requests`).
    System-managed fields (`position`, `notified`, `expired`) are not
    exposed here.
    """

    class Input:
        waitlist_entry_id = graphene.ID(required=True)
        preferred_seats = graphene.List(graphene.Int)
        special_requests = graphene.String()

    waitlist_entry = graphene.Field(WaitlistEntryNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        waitlist_entry_id,
        preferred_seats=None,
        special_requests=None,
    ):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(waitlist_entry_id)
        except Exception:
            raise GraphQLError("Invalid waitlist_entry_id.")

        try:
            entry = WaitlistEntry.objects.select_for_update().get(pk=pk)
        except WaitlistEntry.DoesNotExist:
            raise GraphQLError("Waitlist entry not found.")

        if entry.user_id != user.pk and not user.is_staff:
            raise GraphQLError("Not authorized to update this waitlist entry.")

        update_fields = []

        if preferred_seats is not None:
            entry.preferred_seats = preferred_seats
            update_fields.append("preferred_seats")

        if special_requests is not None:
            entry.special_requests = special_requests
            update_fields.append("special_requests")

        if not update_fields:
            return cls(
                waitlist_entry=entry,
                success=True,
                message="Nothing to update.",
            )

        update_fields.append("updated_at")

        try:
            entry.save(update_fields=update_fields)
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            waitlist_entry=entry,
            success=True,
            message="Waitlist entry updated.",
        )


class LeaveWaitlist(relay.ClientIDMutation):
    """
    Leave a waitlist.

    Soft-leaves by setting `expired=True` (preserves the audit trail and
    allows re-joining via the activate() path). Staff may leave on behalf
    of a user.
    """

    class Input:
        waitlist_entry_id = graphene.ID(required=True)
        hard_delete = graphene.Boolean(default_value=False)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, waitlist_entry_id, hard_delete=False
    ):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        try:
            _, pk = from_global_id(waitlist_entry_id)
        except Exception:
            raise GraphQLError("Invalid waitlist_entry_id.")

        try:
            entry = WaitlistEntry.objects.select_for_update().get(pk=pk)
        except WaitlistEntry.DoesNotExist:
            raise GraphQLError("Waitlist entry not found.")

        if entry.user_id != user.pk and not user.is_staff:
            raise GraphQLError("Not authorized to remove this waitlist entry.")

        if hard_delete:
            if not user.is_staff:
                raise GraphQLError("Only staff may hard-delete waitlist entries.")
            entry.delete()
            return cls(success=True, message="Waitlist entry deleted.")

        if entry.expired:
            return cls(
                success=True,
                message="Waitlist entry is already expired.",
            )

        entry.expired = True
        entry.expired_at = timezone.now()
        entry.save(update_fields=["expired", "expired_at", "updated_at"])

        return cls(success=True, message="Left the waitlist.")


# =============================================================================
# UserPreference
# =============================================================================

class UpsertUserPreference(relay.ClientIDMutation):
    """
    Create or update the caller's ride preferences.

    OneToOneField means create and update collapse into a single
    upsert. `conversation_level` and `temperature_preference` use
    IntegerChoices, so we validate the integer against the enum.
    """

    class Input:
        music_preference = graphene.String()
        conversation_level = graphene.Int()
        temperature_preference = graphene.Int()

    user_preference = graphene.Field(UserPreferenceNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        valid_music = {c.value for c in UserPreference.MusicPreference}
        valid_conversation = {c.value for c in UserPreference.ConversationLevel}
        valid_temperature = {c.value for c in UserPreference.TemperaturePreference}

        # Collect defaults for create path.
        create_defaults = {}

        if "music_preference" in input and input["music_preference"] is not None:
            if input["music_preference"] not in valid_music:
                raise GraphQLError(
                    f"music_preference must be one of: "
                    f"{', '.join(sorted(valid_music))}."
                )
            create_defaults["music_preference"] = input["music_preference"]

        if "conversation_level" in input and input["conversation_level"] is not None:
            if input["conversation_level"] not in valid_conversation:
                raise GraphQLError(
                    f"conversation_level must be one of: "
                    f"{sorted(valid_conversation)}."
                )
            create_defaults["conversation_level"] = input["conversation_level"]

        if "temperature_preference" in input and input["temperature_preference"] is not None:
            if input["temperature_preference"] not in valid_temperature:
                raise GraphQLError(
                    f"temperature_preference must be one of: "
                    f"{sorted(valid_temperature)}."
                )
            create_defaults["temperature_preference"] = input["temperature_preference"]

        preference, created = UserPreference.objects.get_or_create(
            user=user,
            defaults=create_defaults,
        )

        if not created and create_defaults:
            for field, value in create_defaults.items():
                setattr(preference, field, value)
            preference.save(update_fields=list(create_defaults.keys()) + ["updated_at"])

        return cls(
            user_preference=preference,
            success=True,
            message="User preference saved.",
        )


class DeleteUserPreference(relay.ClientIDMutation):
    """
    Delete the caller's ride preferences.

    Staff may delete another user's preferences by passing `user_id`.
    """

    class Input:
        user_id = graphene.ID()  # staff-only

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, user_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")

        target_user = user

        if user_id:
            if not user.is_staff:
                raise GraphQLError("Only staff may delete another user's preferences.")
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                _, pk = from_global_id(user_id)
            except Exception:
                raise GraphQLError("Invalid user_id.")
            try:
                target_user = User.objects.get(pk=pk)
            except User.DoesNotExist:
                raise GraphQLError("User not found.")

        try:
            preference = UserPreference.objects.get(user=target_user)
        except UserPreference.DoesNotExist:
            return cls(
                success=True,
                message="No preferences to delete.",
            )

        preference.delete()

        return cls(success=True, message="User preference deleted.")


# =============================================================================
# Registration
# =============================================================================

class SharedTripMutations(graphene.ObjectType):
    create_shared_trip = CreateSharedTrip.Field()
    update_shared_trip = UpdateSharedTrip.Field()
    delete_shared_trip = DeleteSharedTrip.Field()

    join_waitlist = JoinWaitlist.Field()
    update_waitlist_entry = UpdateWaitlistEntry.Field()
    leave_waitlist = LeaveWaitlist.Field()

    upsert_user_preference = UpsertUserPreference.Field()
    delete_user_preference = DeleteUserPreference.Field()