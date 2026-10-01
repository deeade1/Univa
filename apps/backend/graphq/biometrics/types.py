# apps/backend/graphq/biometrics/types.py

import graphene

from graphene import Node
from graphene_django.types import DjangoObjectType

from biometrics.models import (
    BiometricDevice,
    FaceEncoding,
    FaceVerification,
    FaceVerificationImage,
)


class FaceVerificationNode(DjangoObjectType):
    class Meta:
        model = FaceVerification
        interfaces = (Node,)
        fields = "__all__"


class FaceEncodingNode(DjangoObjectType):
    class Meta:
        model = FaceEncoding
        interfaces = (Node,)
        fields = (
            "id",
            "user",
            "version",
            "is_active",
            "source_image",
            "metadata",
            "created_at",
            "updated_at",
        )


class FaceVerificationImageNode(DjangoObjectType):
    class Meta:
        model = FaceVerificationImage
        interfaces = (Node,)
        fields = "__all__"


class BiometricDeviceNode(DjangoObjectType):
    """
    GraphQL representation of a trusted biometric device.
    """

    device_name = graphene.String()
    user_email = graphene.String()

    class Meta:
        model = BiometricDevice
        interfaces = (Node,)

        fields = [
            "id",
            "user",
            "device_id",
            "trusted",
            "device_info",
            "biometric_hash",
            "last_used_at",
            "registered_at",
        ]

    def resolve_device_name(self, info):
        return self.device_info

    def resolve_user_email(self, info):
        return getattr(
            self.user,
            "email",
            None,
        )