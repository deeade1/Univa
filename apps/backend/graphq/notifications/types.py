from graphene import Node
from graphene_django.types import DjangoObjectType
from notifications.models.device import NotificationDevice

class NotificationDeviceNode(DjangoObjectType):
    class Meta:
        model = NotificationDevice
        fields = (
            "id",
            "platform",
            "provider",
            "device_token",
            "device_id",
            "device_name",
            "app_version",
            "os_version",
            "is_active",
            "notifications_enabled",
            "last_used_at",
            "last_error",
            "created_at",
            "updated_at",
        )
        interfaces = (Node,)
        

        