# apps/backend/graphq/biometrics/schema.py

"""
Biometrics GraphQL schema.

Exposes the biometrics query surface for the top-level schema using
Relay connection fields with django-filter integration.

Mutations live in ``mutations.py`` and are composed separately by the
root schema.

Architecture
------------

GraphQL is a transport layer only.

This module is responsible for:

    - authentication / authorization on reads
    - Relay node resolution
    - filtering on Relay connections
    - shaping model data for GraphQL

It does NOT own:

    - ArcFace processing
    - pgvector queries
    - face matching
    - verification state machine
    - liveness policy

Those responsibilities belong to biometrics.services.*.
"""

from __future__ import annotations

import django_filters
import graphene
from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError

from univa_jwt.decorators import login_required

from biometrics.models import (
    BiometricDevice,
    FaceEncoding,
    FaceVerification,
    FaceVerificationImage,
)

from graphq.biometrics.types import (
    BiometricDeviceNode,
    FaceEncodingNode,
    FaceVerificationImageNode,
    FaceVerificationNode,
)


# ============================================================================
# FILTERS
# ============================================================================


class BiometricDeviceFilter(django_filters.FilterSet):
    trusted = django_filters.BooleanFilter()
    device_id = django_filters.CharFilter(lookup_expr="iexact")
    device_info = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = BiometricDevice
        fields = ["trusted", "device_id", "device_info"]


class FaceEncodingFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    version = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = FaceEncoding
        fields = ["is_active", "version"]


class FaceVerificationImageFilter(django_filters.FilterSet):
    is_verified = django_filters.BooleanFilter()
    face_detected = django_filters.BooleanFilter()

    class Meta:
        model = FaceVerificationImage
        fields = ["is_verified", "face_detected"]


class FaceVerificationFilter(django_filters.FilterSet):
    is_verified = django_filters.BooleanFilter()
    verification_method = django_filters.CharFilter(lookup_expr="iexact")
    verification_channel = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = FaceVerification
        fields = ["is_verified", "verification_method", "verification_channel"]


# ============================================================================
# HELPERS
# ============================================================================


def _get_authenticated_user(info):
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


# ============================================================================
# QUERY ROOT
# ============================================================================


class BiometricsQueries(graphene.ObjectType):
    """
    Read-only biometric state exposed through Relay connections.

    Cross-user queries are deliberately not exposed: biometric state
    belongs to the owning user only. Every resolver below scopes its
    queryset to ``info.context.user``.
    """

    # ------------------------------------------------------------------
    # Relay node lookups (global-id based)
    # ------------------------------------------------------------------

    biometric_device = Node.Field(BiometricDeviceNode)
    face_encoding = Node.Field(FaceEncodingNode)
    face_verification = Node.Field(FaceVerificationNode)
    face_verification_image = Node.Field(FaceVerificationImageNode)

    # ------------------------------------------------------------------
    # Current user's biometric state (connection fields)
    # ------------------------------------------------------------------

    my_biometric_devices = DjangoFilterConnectionField(
        BiometricDeviceNode,
        filterset_class=BiometricDeviceFilter,
        description="Trusted biometric devices registered by the current user.",
    )

    my_face_encodings = DjangoFilterConnectionField(
        FaceEncodingNode,
        filterset_class=FaceEncodingFilter,
        description="Face encodings owned by the current user.",
    )

    my_face_verification_images = DjangoFilterConnectionField(
        FaceVerificationImageNode,
        filterset_class=FaceVerificationImageFilter,
        description="Face verification images owned by the current user.",
    )

    # `my_face_verification` is a one-to-one relation — no connection needed.
    my_face_verification = graphene.Field(
        FaceVerificationNode,
        description="Biometric verification state for the authenticated user.",
    )

    # ------------------------------------------------------------------
    # Connection resolvers
    # ------------------------------------------------------------------


    @login_required
    def resolve_my_biometric_devices(self, info, **kwargs):
        user = _get_authenticated_user(info)
        qs = BiometricDevice.objects.filter(user=user)

        import logging
        logging.getLogger("biometrics.debug").warning(
            "resolve_my_biometric_devices user_pk=%s count=%s kwargs=%s",
            user.pk, qs.count(), kwargs,
        )

        return qs
    @login_required
    def resolve_my_face_encodings(self, info, **kwargs):
        user = _get_authenticated_user(info)
        qs = FaceEncoding.objects.filter(user=user)

        import logging
        logging.getLogger("biometrics.debug").warning(
            "resolve_my_face_encodings user_pk=%s count=%s kwargs=%s",
            user.pk, qs.count(), kwargs,
        )

        return qs

    
    @login_required
    def resolve_my_face_verification_images(self, info, **kwargs):
        user = _get_authenticated_user(info)
        qs = FaceVerificationImage.objects.filter(user=user)

        import logging
        logging.getLogger("biometrics.debug").warning(
            "resolve_my_face_verification_images user_pk=%s count=%s kwargs=%s",
            user.pk, qs.count(), kwargs,
        )

        return qs
    # ------------------------------------------------------------------
    # Single-object resolver
    # ------------------------------------------------------------------

    @login_required
    def resolve_my_face_verification(self, info):
        user = _get_authenticated_user(info)
        try:
            return user.face_verification
        except FaceVerification.DoesNotExist:
            return None


# ============================================================================
# PUBLIC API
# ============================================================================


__all__ = [
    "BiometricsQueries",
]