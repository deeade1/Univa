import graphene
from graphene import relay
from notifications.models.device import NotificationDevice


class RegisterNotificationDevice(relay.ClientIDMutation):
    """
    Register or update the authenticated user's notification device.

    Supports:
        - Expo
        - FCM
        - APNs
        - WebPush
        - Other registered providers

    Uses Relay ClientIDMutation.
    """

    class Input:
        device_token = graphene.String(required=True)
        platform = graphene.String(required=True)

        provider = graphene.String(required=False)

        device_id = graphene.String(required=False)
        device_name = graphene.String(required=False)

        app_version = graphene.String(required=False)
        os_version = graphene.String(required=False)

        notifications_enabled = graphene.Boolean(required=False)

    notification_device = graphene.Field(
        NotificationDeviceType
    )

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user or not user.is_authenticated:
            raise Exception("Authentication required.")

        # --------------------------------------------------------------
        # Required fields
        # --------------------------------------------------------------

        device_token = (input.get("device_token") or "").strip()
        platform = (input.get("platform") or "").strip().lower()

        if not device_token:
            raise Exception("Device token is required.")

        if not platform:
            raise Exception("Platform is required.")

        # --------------------------------------------------------------
        # Provider
        # --------------------------------------------------------------

        provider = (
            (data.get("provider") or "").strip().lower()
            or NotificationDevice.Provider.EXPO
        )

        # --------------------------------------------------------------
        # Validate enum values
        # --------------------------------------------------------------

        valid_platforms = {
            choice.value
            for choice in NotificationDevice.Platform
        }

        valid_providers = {
            choice.value
            for choice in NotificationDevice.Provider
        }

        if platform not in valid_platforms:
            raise Exception(
                f"Invalid platform '{platform}'. "
                f"Expected one of: "
                f"{', '.join(sorted(valid_platforms))}."
            )

        if provider not in valid_providers:
            raise Exception(
                f"Invalid provider '{provider}'. "
                f"Expected one of: "
                f"{', '.join(sorted(valid_providers))}."
            )

        # --------------------------------------------------------------
        # Expo token validation
        # --------------------------------------------------------------

        if provider == NotificationDevice.Provider.EXPO:
            expo_pattern = re.compile(
                r"^(ExponentPushToken|ExpoPushToken)\[[^\]]+\]$"
            )

            if not expo_pattern.match(device_token):
                raise Exception(
                    "Invalid Expo push token. "
                    "Expected ExponentPushToken[...] "
                    "or ExpoPushToken[...]."
                )

        # --------------------------------------------------------------
        # Optional fields
        # --------------------------------------------------------------

        device_id = (
            input.get("device_id") or ""
        ).strip()

        device_name = (
            input.get("device_name") or ""
        ).strip()

        app_version = (
            input.get("app_version") or ""
        ).strip()

        os_version = (
            input.get("os_version") or ""
        ).strip()

        notifications_enabled = input.get(
            "notifications_enabled",
            True,
        )

        # --------------------------------------------------------------
        # Register / update device
        # --------------------------------------------------------------

        notification_device, created = (
            NotificationDevice.objects.update_or_create(
                device_token=device_token,
                defaults={
                    "user": user,
                    "platform": platform,
                    "provider": provider,
                    "device_id": device_id,
                    "device_name": device_name,
                    "app_version": app_version,
                    "os_version": os_version,
                    "is_active": True,
                    "notifications_enabled": notifications_enabled,
                    "last_used_at": timezone.now(),
                    "last_error": "",
                },
            )
        )

        return cls(
            notification_device=notification_device,
            success=True,
            message=(
                "Notification device registered successfully."
                if created
                else "Notification device updated successfully."
            ),
        )              

class NotificationMutations(graphene.ObjectType):
    
    register_notification_device = RegisterNotificationDevice.Field()