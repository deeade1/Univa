# apps/backend/graphq/transport/mutations/rating.py
"""
Mutations for Rating, ProviderRating, and CustomerRating.

Ownership rules enforced:
    - A rater is always the authenticated user; the client never supplies it.
    - Only the customer who posted a ProviderRating may edit or delete it.
    - Only the provider who posted a CustomerRating may edit or delete it.
    - Provider responses go through a dedicated mutation that requires the
      responding user to own the provider profile.
    - `is_verified` and `is_public` are staff-controlled.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from graphene import relay
import graphene
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphq.transport.types.ratings import (
    RatingNode,
    ProviderRatingNode,
    CustomerRatingNode
)
from graphq.transport.types.service_request import ServiceRequestNode
from graphq.transport.types.service_provider import   ServiceProviderProfileNode

from graphq.accounts.types.user import UserNode

from transport.models.core.service_request import ServiceRequest
from transport.models.core.service_provider import ServiceProviderProfile
from transport.models.rating.ratings import (
    Rating,
    ProviderRating,
    CustomerRating,
    update_provider_rating,
)


# =============================================================================
# Helpers
# =============================================================================

def _resolve(model, global_id, label=None):
    try:
        _, pk = from_global_id(global_id)
    except Exception:
        raise GraphQLError(f"Invalid {label or model.__name__} id.")
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{label or model.__name__} not found.")


def _validate_score(value, field):
    if value is None:
        return
    if not isinstance(value, int) or not 1 <= value <= 5:
        raise GraphQLError(f"{field} must be an integer between 1 and 5.")


# =============================================================================
# Legacy Rating (rater -> rated_user, tied to a ServiceRequest)
# =============================================================================

class CreateRating(relay.ClientIDMutation):
    """
    Create a legacy Rating.

    The rater is the authenticated user. `service_request_id` may point
    at any ServiceRequest the rater participated in (trip, delivery,
    shared, etc.).
    """

    class Input:
        rated_user_id = graphene.ID(required=True)
        service_request_id = graphene.ID(required=True)
        score = graphene.Int(required=True)
        comment = graphene.String()

    rating = graphene.Field(RatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, rated_user_id, service_request_id, score, comment=None
    ):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        _validate_score(score, "score")

        rated_user = _resolve(
            type(me), rated_user_id, label="rated_user"
        )
        if rated_user.pk == me.pk:
            raise GraphQLError("Cannot rate yourself.")

        service_request = _resolve(
            ServiceRequest, service_request_id, label="service_request"
        )

        # Only participants may rate the ServiceRequest.
        is_customer = service_request.customer_id == me.pk
        is_provider = (
            service_request.provider_id
            and getattr(me, "service_provider", None)
            and me.service_provider.pk == service_request.provider_id
        )
        if not (is_customer or is_provider or me.is_staff):
            raise GraphQLError(
                "Only participants of this service request may rate it."
            )

        if Rating.objects.filter(
            rater=me, rated_user=rated_user, trip=service_request
        ).exists():
            raise GraphQLError(
                "You have already rated this user for this service request."
            )

        try:
            rating = Rating.objects.create(
                rater=me,
                rated_user=rated_user,
                trip=service_request,
                score=score,
                comment=comment or "",
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            rating=rating,
            success=True,
            message="Rating created.",
        )


class UpdateRating(relay.ClientIDMutation):
    """
    Update the score and/or comment on a legacy Rating.

    Only the original rater (or staff) may update.
    """

    class Input:
        rating_id = graphene.ID(required=True)
        score = graphene.Int()
        comment = graphene.String()

    rating = graphene.Field(RatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, rating_id, score=None, comment=None
    ):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(Rating, rating_id, label="rating")

        if rating.rater_id != me.pk and not me.is_staff:
            raise GraphQLError("Only the original rater may edit this rating.")

        if score is not None:
            _validate_score(score, "score")
            rating.score = score

        if comment is not None:
            rating.comment = comment

        try:
            rating.full_clean()
            rating.save()
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            rating=rating,
            success=True,
            message="Rating updated.",
        )


class DeleteRating(relay.ClientIDMutation):
    """Delete a legacy Rating. Rater or staff only."""

    class Input:
        rating_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, rating_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(Rating, rating_id, label="rating")

        if rating.rater_id != me.pk and not me.is_staff:
            raise GraphQLError("Only the original rater may delete this rating.")

        rating.delete()

        return cls(success=True, message="Rating deleted.")


# =============================================================================
# ProviderRating (customer rates a provider)
# =============================================================================

class CreateProviderRating(relay.ClientIDMutation):
    """
    Create a rating for a service provider.

    The customer is always the authenticated user. `is_verified` is set
    automatically if the customer has a completed ServiceRequest with
    this provider — otherwise the mutation leaves it False. `is_public`
    is only adjustable by staff.
    """

    class Input:
        provider_id = graphene.ID(required=True)
        service_request_id = graphene.ID()

        overall_rating = graphene.Int(required=True)

        punctuality = graphene.Int()
        professionalism = graphene.Int()
        communication = graphene.Int()
        service_quality = graphene.Int()
        value_for_money = graphene.Int()
        vehicle_condition = graphene.Int()
        safety = graphene.Int()

        review = graphene.String()
        photos = graphene.List(graphene.String)
        metadata = graphene.JSONString()

    provider_rating = graphene.Field(ProviderRatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, provider_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        _validate_score(input["overall_rating"], "overall_rating")

        for field_name in (
            "punctuality",
            "professionalism",
            "communication",
            "service_quality",
            "value_for_money",
            "vehicle_condition",
            "safety",
        ):
            _validate_score(input.get(field_name), field_name)

        provider = _resolve(
            ServiceProviderProfile, provider_id, label="provider"
        )

        if provider.user_id == me.pk:
            raise GraphQLError("Cannot rate yourself.")

        service_request = None
        if input.get("service_request_id"):
            service_request = _resolve(
                ServiceRequest,
                input["service_request_id"],
                label="service_request",
            )
            if service_request.provider_id != provider.pk:
                raise GraphQLError(
                    "The service request is not assigned to this provider."
                )
            if service_request.customer_id != me.pk and not me.is_staff:
                raise GraphQLError(
                    "Only the customer of the service request may rate it."
                )

        # Duplicate guard mirrors the model UniqueConstraint.
        existing = ProviderRating.objects.filter(
            provider=provider,
            customer=me,
            service_request=service_request,
        ).first()
        if existing:
            raise GraphQLError(
                "You have already rated this provider for this service request."
            )

        # Auto-verify when the customer completed a service with this provider.
        auto_verified = bool(
            service_request
            and service_request.status == ServiceRequest.Status.COMPLETED
            and service_request.customer_id == me.pk
        )

        is_public = True
        if "is_public" in input and me.is_staff:
            is_public = bool(input["is_public"])

        try:
            rating = ProviderRating.objects.create(
                provider=provider,
                customer=me,
                service_request=service_request,
                overall_rating=input["overall_rating"],
                punctuality=input.get("punctuality"),
                professionalism=input.get("professionalism"),
                communication=input.get("communication"),
                service_quality=input.get("service_quality"),
                value_for_money=input.get("value_for_money"),
                vehicle_condition=input.get("vehicle_condition"),
                safety=input.get("safety"),
                review=input.get("review") or "",
                photos=input.get("photos") or [],
                metadata=input.get("metadata") or {},
                is_verified=auto_verified,
                is_public=is_public,
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        # Refresh the aggregate on the provider profile.
        update_provider_rating(provider)

        return cls(
            provider_rating=rating,
            success=True,
            message="Provider rating created.",
        )


class UpdateProviderRating(relay.ClientIDMutation):
    """
    Update a ProviderRating.

    Only the rating's customer (or staff) may edit. Fields update
    individually; `is_verified` and `is_public` are staff-only. Each
    edit is appended to `edit_history` via the model's `edit_rating()`.
    """

    class Input:
        provider_rating_id = graphene.ID(required=True)

        overall_rating = graphene.Int()
        punctuality = graphene.Int()
        professionalism = graphene.Int()
        communication = graphene.Int()
        service_quality = graphene.Int()
        value_for_money = graphene.Int()
        vehicle_condition = graphene.Int()
        safety = graphene.Int()

        review = graphene.String()
        photos = graphene.List(graphene.String)
        metadata = graphene.JSONString()

        is_verified = graphene.Boolean()   # staff-only
        is_public = graphene.Boolean()     # staff-only

    provider_rating = graphene.Field(ProviderRatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, provider_rating_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(
            ProviderRating, provider_rating_id, label="provider_rating"
        )

        if rating.customer_id != me.pk and not me.is_staff:
            raise GraphQLError("Only the rating's author may edit it.")

        # Staff-only flags
        for flag in ("is_verified", "is_public"):
            if flag in input and input[flag] is not None and not me.is_staff:
                raise GraphQLError(f"Only staff may change {flag}.")

        scalar_map = {
            "overall_rating": "overall_rating",
            "punctuality": "punctuality",
            "professionalism": "professionalism",
            "communication": "communication",
            "service_quality": "service_quality",
            "value_for_money": "value_for_money",
            "vehicle_condition": "vehicle_condition",
            "safety": "safety",
            "review": "review",
            "photos": "photos",
            "metadata": "metadata",
        }

        to_apply = {}
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                if model_field in (
                    "overall_rating",
                    "punctuality",
                    "professionalism",
                    "communication",
                    "service_quality",
                    "value_for_money",
                    "vehicle_condition",
                    "safety",
                ):
                    _validate_score(input[input_key], input_key)
                to_apply[model_field] = input[input_key]

        # Route user-facing edits through the model's edit_rating so the
        # edit_history is recorded consistently. Staff flag flips are
        # written directly to avoid polluting the customer edit history.
        if to_apply:
            rating.edit_rating(**to_apply)

        staff_updates = []
        if "is_verified" in input and input["is_verified"] is not None:
            rating.is_verified = input["is_verified"]
            staff_updates.append("is_verified")
        if "is_public" in input and input["is_public"] is not None:
            rating.is_public = input["is_public"]
            staff_updates.append("is_public")
        if staff_updates:
            rating.save(update_fields=staff_updates + ["updated_at"])

        # Aggregate refresh.
        update_provider_rating(rating.provider)

        return cls(
            provider_rating=rating,
            success=True,
            message="Provider rating updated.",
        )


class RespondToProviderRating(relay.ClientIDMutation):
    """
    Provider response to a rating they received.

    Ownership: the caller must own the `ServiceProviderProfile` being
    rated, or be staff.
    """

    class Input:
        provider_rating_id = graphene.ID(required=True)
        response = graphene.String(required=True)

    provider_rating = graphene.Field(ProviderRatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(
        cls, root, info, provider_rating_id, response
    ):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(
            ProviderRating, provider_rating_id, label="provider_rating"
        )

        is_owner = (
            getattr(me, "service_provider", None)
            and me.service_provider.pk == rating.provider_id
        )
        if not (is_owner or me.is_staff):
            raise GraphQLError(
                "Only the rated provider may respond to this rating."
            )

        rating.respond(response)
        return cls(
            provider_rating=rating,
            success=True,
            message="Response recorded.",
        )


class DeleteProviderRating(relay.ClientIDMutation):
    """Delete a ProviderRating. Author or staff only."""

    class Input:
        provider_rating_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, provider_rating_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(
            ProviderRating, provider_rating_id, label="provider_rating"
        )

        if rating.customer_id != me.pk and not me.is_staff:
            raise GraphQLError("Only the rating's author may delete it.")

        provider = rating.provider
        rating.delete()

        # Refresh the aggregate.
        update_provider_rating(provider)

        return cls(success=True, message="Provider rating deleted.")


# =============================================================================
# CustomerRating (provider rates a customer)
# =============================================================================

class CreateCustomerRating(relay.ClientIDMutation):
    """
    Create a rating for a customer.

    The provider is derived from the authenticated user's
    `service_provider` profile. The caller must own a provider profile.
    """

    class Input:
        customer_id = graphene.ID(required=True)
        service_request_id = graphene.ID()

        overall_rating = graphene.Int(required=True)
        punctuality = graphene.Int()
        communication = graphene.Int()
        behavior = graphene.Int()
        respect = graphene.Int()

        review = graphene.String()

    customer_rating = graphene.Field(CustomerRatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, customer_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        provider = getattr(me, "service_provider", None)
        if provider is None:
            raise GraphQLError(
                "You must have a service provider profile to rate customers."
            )

        _validate_score(input["overall_rating"], "overall_rating")
        for field_name in ("punctuality", "communication", "behavior", "respect"):
            _validate_score(input.get(field_name), field_name)

        customer = _resolve(
            type(me), customer_id, label="customer"
        )
        if customer.pk == me.pk:
            raise GraphQLError("Cannot rate yourself.")

        service_request = None
        if input.get("service_request_id"):
            service_request = _resolve(
                ServiceRequest,
                input["service_request_id"],
                label="service_request",
            )
            if service_request.provider_id != provider.pk:
                raise GraphQLError(
                    "The service request is not assigned to you."
                )
            if service_request.customer_id != customer.pk:
                raise GraphQLError(
                    "The service request is not for this customer."
                )

        if CustomerRating.objects.filter(
            customer=customer,
            provider=provider,
            service_request=service_request,
        ).exists():
            raise GraphQLError(
                "You have already rated this customer for this service request."
            )

        try:
            rating = CustomerRating.objects.create(
                customer=customer,
                provider=provider,
                service_request=service_request,
                overall_rating=input["overall_rating"],
                punctuality=input.get("punctuality"),
                communication=input.get("communication"),
                behavior=input.get("behavior"),
                respect=input.get("respect"),
                review=input.get("review") or "",
            )
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            customer_rating=rating,
            success=True,
            message="Customer rating created.",
        )


class UpdateCustomerRating(relay.ClientIDMutation):
    """
    Update a CustomerRating.

    Only the provider who authored the rating (or staff) may edit.
    """

    class Input:
        customer_rating_id = graphene.ID(required=True)

        overall_rating = graphene.Int()
        punctuality = graphene.Int()
        communication = graphene.Int()
        behavior = graphene.Int()
        respect = graphene.Int()

        review = graphene.String()
        is_public = graphene.Boolean()  # staff-only

    customer_rating = graphene.Field(CustomerRatingNode)
    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, customer_rating_id, **input):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(
            CustomerRating, customer_rating_id, label="customer_rating"
        )

        is_owner = (
            getattr(me, "service_provider", None)
            and me.service_provider.pk == rating.provider_id
        )
        if not (is_owner or me.is_staff):
            raise GraphQLError("Only the rating's author may edit it.")

        if "is_public" in input and input["is_public"] is not None and not me.is_staff:
            raise GraphQLError("Only staff may change is_public.")

        scalar_map = {
            "overall_rating": "overall_rating",
            "punctuality": "punctuality",
            "communication": "communication",
            "behavior": "behavior",
            "respect": "respect",
            "review": "review",
        }

        changed = []
        for input_key, model_field in scalar_map.items():
            if input_key in input and input[input_key] is not None:
                if model_field == "overall_rating":
                    _validate_score(input[input_key], input_key)
                elif model_field in ("punctuality", "communication", "behavior", "respect"):
                    _validate_score(input[input_key], input_key)
                setattr(rating, model_field, input[input_key])
                changed.append(model_field)

        if "is_public" in input and input["is_public"] is not None:
            rating.is_public = input["is_public"]
            changed.append("is_public")

        if not changed:
            return cls(
                customer_rating=rating,
                success=True,
                message="Nothing to update.",
            )

        rating.is_edited = True
        changed.append("is_edited")

        try:
            rating.full_clean()
            rating.save(update_fields=sorted(set(changed + ["updated_at"])))
        except ValidationError as exc:
            raise GraphQLError(f"Validation failed: {exc.message_dict}")

        return cls(
            customer_rating=rating,
            success=True,
            message="Customer rating updated.",
        )


class DeleteCustomerRating(relay.ClientIDMutation):
    """Delete a CustomerRating. Author or staff only."""

    class Input:
        customer_rating_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, customer_rating_id):
        me = info.context.user
        if not me.is_authenticated:
            raise GraphQLError("Authentication required.")

        rating = _resolve(
            CustomerRating, customer_rating_id, label="customer_rating"
        )

        is_owner = (
            getattr(me, "service_provider", None)
            and me.service_provider.pk == rating.provider_id
        )
        if not (is_owner or me.is_staff):
            raise GraphQLError("Only the rating's author may delete it.")

        rating.delete()

        return cls(success=True, message="Customer rating deleted.")


# =============================================================================
# Registration
# =============================================================================

class RatingMutations(graphene.ObjectType):
    # Legacy Rating
    create_rating = CreateRating.Field()
    update_rating = UpdateRating.Field()
    delete_rating = DeleteRating.Field()

    # ProviderRating
    create_provider_rating = CreateProviderRating.Field()
    update_provider_rating = UpdateProviderRating.Field()
    respond_to_provider_rating = RespondToProviderRating.Field()
    delete_provider_rating = DeleteProviderRating.Field()

    # CustomerRating
    create_customer_rating = CreateCustomerRating.Field()
    update_customer_rating = UpdateCustomerRating.Field()
    delete_customer_rating = DeleteCustomerRating.Field()