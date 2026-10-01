# apps/backend/graphq/accounts/types/user_profile.py
"""
GraphQL node for accounts.UserProfile.

Security notes
--------------
`pin_hash` is never exposed. The node declares only `has_pin` as a
boolean field; the hash column itself is excluded from `fields`.

`interest_vector` is intentionally not exposed. It's stored as a
pgvector VectorField when available, otherwise as a JSONField — either
way it's an internal recommendation artifact, not a client-facing field.

`ResizedImageField` columns (`profile_picture`, `id_image`) are exposed
as strings but are only filterable by `isnull` — django-filter cannot
build `exact` filters for ResizedImageField without an override, and
matching the storage path is rarely useful anyway.
"""

import graphene
from graphene import relay, Node
from graphene_django import DjangoObjectType

from accounts.models.profile import UserProfile


class UserProfileNode(DjangoObjectType):
    """
    Centralized user profile.
    """

    # ------------------------------------------------------------------
    # Derived booleans (from methods/properties on the model)
    # ------------------------------------------------------------------

    has_pin = graphene.Boolean(
        description="Whether the user has a PIN set. The hash is never exposed."
    )
    is_verified = graphene.Boolean(
        description="True when verification_status is anything but 'unverified'."
    )
    verification_level = graphene.Int(
        description="Numeric verification level (0-5)."
    )
    verification_badge = graphene.String(
        description="Human-readable verification status label."
    )
    age = graphene.Int(
        description="Age in years, derived from date_of_birth. Null if unset."
    )
    display_name = graphene.String(
        description="Best available human-readable display name."
    )

    class Meta:
        model = UserProfile
        interfaces = (Node,)
        # Explicit field list — never expose `pin_hash`, `search_document`,
        # or `interest_vector`.
        fields = "__all__"
        filter_fields = {
            # ---- Ownership (forward OneToOne) --------------------------
            "user": ["exact"],
            "user__email": ["exact", "icontains"],
            "user__first_name": ["exact", "icontains"],
            "univa_id": ["exact"],

            # ---- Verification -------------------------------------------
            "verification_status": ["exact", "in"],
            "verification_date": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "verified_by": ["exact"],

            # ---- Identification ----------------------------------------
            "id_type": ["exact", "in"],
            "id_number": ["exact"],
            "date_of_birth": ["exact", "gte", "lte", "lt", "gt", "isnull"],
            "gender": ["exact", "in"],

            # ---- Business identity -------------------------------------
            "is_business": ["exact"],
            "company_name": ["exact", "icontains"],

            # ---- Preferences -------------------------------------------
            "language_code": ["exact", "in"],
            "preferred_notification_method": ["exact", "in"],

            # ---- Presence / activity -----------------------------------
            "is_online": ["exact"],
            "last_active": ["exact", "gte", "lte", "lt", "gt"],

            # ---- Ratings / counters ------------------------------------
            "rating": ["exact", "gte", "lte", "lt", "gt"],
            "loyalty_points": ["exact", "gte", "lte"],
            "follower_count": ["exact", "gte", "lte"],
            "following_count": ["exact", "gte", "lte"],
            "likes_count": ["exact", "gte", "lte"],
            "video_count": ["exact", "gte", "lte"],

            # ---- Images (presence only) --------------------------------
            "profile_picture": ["isnull"],
            "id_image": ["isnull"],

            # ---- Timestamps --------------------------------------------
            "created_at": ["exact", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "gte", "lte", "lt", "gt"],
        }

    # ------------------------------------------------------------------
    # Resolvers for declared fields
    # ------------------------------------------------------------------

    def resolve_has_pin(self, info):
        return self.has_pin

    def resolve_is_verified(self, info):
        return self.is_verified

    def resolve_verification_level(self, info):
        return self.verification_level

    def resolve_verification_badge(self, info):
        return str(self.get_verification_badge())

    def resolve_age(self, info):
        return self.age

    def resolve_display_name(self, info):
        return self.display_name