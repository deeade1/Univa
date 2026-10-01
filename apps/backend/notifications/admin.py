"""
Django Admin configuration for the Univa notification system.

Provides operational visibility into:

    - NotificationEvent
    - UserNotification
    - NotificationPreference
    - NotificationDevice
    - NotificationPush

Admin is intentionally focused on monitoring and safe state inspection.
Provider delivery itself remains handled by the notification task/channel
architecture.
"""

from django.contrib import admin

from notifications.models.device import NotificationDevice
from notifications.models.event import NotificationEvent
from notifications.models.notification import UserNotification
from notifications.models.preference import NotificationPreference
from notifications.models.push import NotificationPush


# ============================================================================
# NOTIFICATION EVENT
# ============================================================================


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "module",
        "event_type",
        "actor",
        "status",
        "attempts",
        "created_at",
        "processed_at",
    )

    list_filter = (
        "status",
        "module",
        "created_at",
    )

    search_fields = (
        "event_type",
        "module",
        "object_type",
        "object_id",
        "error_message",
        "actor__email",
        "actor__phone_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "processed_at",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_per_page = 50

    fieldsets = (
        (
            "Event Identity",
            {
                "fields": (
                    "event_type",
                    "module",
                    "actor",
                )
            },
        ),
        (
            "Target",
            {
                "fields": (
                    "object_type",
                    "object_id",
                )
            },
        ),
        (
            "Payload",
            {
                "fields": (
                    "payload",
                )
            },
        ),
        (
            "Processing",
            {
                "fields": (
                    "status",
                    "attempts",
                    "error_message",
                    "processed_at",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# ============================================================================
# USER NOTIFICATION
# ============================================================================


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "module",
        "notification_type",
        "priority",
        "title",
        "is_read",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "module",
        "notification_type",
        "priority",
        "is_read",
        "is_archived",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "module",
        "recipient__email",
        "recipient__phone_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "read_at",
        "archived_at",
    )

    autocomplete_fields = (
        "recipient",
        "event",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_per_page = 50

    fieldsets = (
        (
            "Recipient",
            {
                "fields": (
                    "recipient",
                    "event",
                )
            },
        ),
        (
            "Notification",
            {
                "fields": (
                    "module",
                    "notification_type",
                    "priority",
                    "title",
                    "message",
                )
            },
        ),
        (
            "Navigation",
            {
                "fields": (
                    "action_url",
                    "metadata",
                )
            },
        ),
        (
            "State",
            {
                "fields": (
                    "is_read",
                    "read_at",
                    "is_archived",
                    "archived_at",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# ============================================================================
# NOTIFICATION PREFERENCE
# ============================================================================


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notifications_enabled",
        "in_app_enabled",
        "push_enabled",
        "email_enabled",
        "frequency",
        "quiet_hours_enabled",
        "updated_at",
    )

    list_filter = (
        "notifications_enabled",
        "in_app_enabled",
        "push_enabled",
        "email_enabled",
        "frequency",
        "quiet_hours_enabled",
        "marketing_enabled",
        "transactional_enabled",
        "security_enabled",
        "social_enabled",
    )

    search_fields = (
        "user__email",
        "user__phone_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "user",
    )

    ordering = (
        "-updated_at",
    )

    list_per_page = 50

    fieldsets = (
        (
            "User",
            {
                "fields": (
                    "user",
                )
            },
        ),
        (
            "Global Settings",
            {
                "fields": (
                    "notifications_enabled",
                )
            },
        ),
        (
            "Delivery Channels",
            {
                "fields": (
                    "in_app_enabled",
                    "push_enabled",
                    "email_enabled",
                )
            },
        ),
        (
            "Frequency",
            {
                "fields": (
                    "frequency",
                )
            },
        ),
        (
            "Quiet Hours",
            {
                "fields": (
                    "quiet_hours_enabled",
                    "quiet_hours_start",
                    "quiet_hours_end",
                )
            },
        ),
        (
            "Categories",
            {
                "fields": (
                    "marketing_enabled",
                    "transactional_enabled",
                    "security_enabled",
                    "social_enabled",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# ============================================================================
# NOTIFICATION DEVICE
# ============================================================================


@admin.register(NotificationDevice)
class NotificationDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "platform",
        "provider",
        "device_name",
        "is_active",
        "notifications_enabled",
        "last_used_at",
        "updated_at",
    )

    list_filter = (
        "platform",
        "provider",
        "is_active",
        "notifications_enabled",
        "created_at",
    )

    search_fields = (
        "device_token",
        "device_id",
        "device_name",
        "user__email",
        "user__phone_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_used_at",
    )

    autocomplete_fields = (
        "user",
    )

    ordering = (
        "-last_used_at",
        "-created_at",
    )

    list_per_page = 50

    fieldsets = (
        (
            "Owner",
            {
                "fields": (
                    "user",
                )
            },
        ),
        (
            "Device",
            {
                "fields": (
                    "platform",
                    "provider",
                    "device_token",
                    "device_id",
                    "device_name",
                )
            },
        ),
        (
            "Application",
            {
                "fields": (
                    "app_version",
                    "os_version",
                )
            },
        ),
        (
            "State",
            {
                "fields": (
                    "is_active",
                    "notifications_enabled",
                    "last_error",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "last_used_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# ============================================================================
# NOTIFICATION PUSH
# ============================================================================


@admin.register(NotificationPush)
class NotificationPushAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "notification",
        "device",
        "provider",
        "status",
        "attempts",
        "provider_message_id",
        "created_at",
        "sent_at",
    )

    list_filter = (
        "status",
        "provider",
        "created_at",
        "sent_at",
    )

    search_fields = (
        "provider_message_id",
        "error_message",
        "notification__title",
        "notification__message",
        "device__device_token",
        "device__device_id",
        "device__user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "processing_started_at",
        "sent_at",
    )

    autocomplete_fields = (
        "notification",
        "device",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_per_page = 50

    fieldsets = (
        (
            "Delivery",
            {
                "fields": (
                    "notification",
                    "device",
                    "provider",
                    "provider_message_id",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "attempts",
                    "error_message",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "processing_started_at",
                    "sent_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
