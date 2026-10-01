"""

Notification device model for Univa.



Stores registered devices capable of receiving push notifications.



Supported providers:



    - Expo

    - Firebase Cloud Messaging (FCM)

    - Apple Push Notification Service (APNs)

    - Web Push

    - Future providers



This model stores device registration and eligibility state only.



It does NOT:



    - send notifications

    - call push providers

    - dispatch Celery tasks

    - contain provider-specific delivery logic



Provider delivery belongs to:



    notifications.channels.*



Task orchestration belongs to:



    notifications.tasks.*

"""



from __future__ import annotations



from django.conf import settings

from django.db import models

from django.utils import timezone





class NotificationDevice(models.Model):

    """

    Stores a user's registered notification device.



    A user may have multiple devices, for example:



        User

        ├── Android / Expo

        ├── iPhone / APNs

        └── Web / WebPush

    """



    # ======================================================================

    # ENUMS

    # ======================================================================



    class Platform(models.TextChoices):

        ANDROID = "android", "Android"

        IOS = "ios", "iOS"

        WEB = "web", "Web"

        OTHER = "other", "Other"



    class Provider(models.TextChoices):

        EXPO = "expo", "Expo"

        FCM = "fcm", "Firebase Cloud Messaging"

        APNS = "apns", "Apple Push Notification Service"

        WEBPUSH = "webpush", "Web Push"

        OTHER = "other", "Other"



    # ======================================================================

    # OWNER

    # ======================================================================



    user = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.CASCADE,

        related_name="notification_devices",

        db_index=True,

        help_text="User who owns this notification device.",

    )



    # ======================================================================

    # DEVICE INFORMATION

    # ======================================================================



    platform = models.CharField(

        max_length=20,

        choices=Platform.choices,

        default=Platform.OTHER,

        db_index=True,

    )



    provider = models.CharField(

        max_length=20,

        choices=Provider.choices,

        default=Provider.OTHER,

        db_index=True,

    )



    device_token = models.TextField(

        unique=True,

        help_text=(

            "Push token supplied by the notification provider."

        ),

    )



    device_id = models.CharField(

        max_length=255,

        blank=True,

        default="",

        help_text=(

            "Optional physical/device identifier supplied by the client."

        ),

    )



    device_name = models.CharField(

        max_length=255,

        blank=True,

        default="",

    )



    app_version = models.CharField(

        max_length=50,

        blank=True,

        default="",

    )



    os_version = models.CharField(

        max_length=50,

        blank=True,

        default="",

    )



    # ======================================================================

    # STATE

    # ======================================================================



    is_active = models.BooleanField(

        default=True,

        db_index=True,

    )



    notifications_enabled = models.BooleanField(

        default=True,

    )



    last_used_at = models.DateTimeField(

        null=True,

        blank=True,

        db_index=True,

    )



    last_error = models.TextField(

        blank=True,

        default="",

    )



    # ======================================================================

    # TIMESTAMPS

    # ======================================================================



    created_at = models.DateTimeField(

        auto_now_add=True,

    )



    updated_at = models.DateTimeField(

        auto_now=True,

    )



    # ======================================================================

    # META

    # ======================================================================



    class Meta:

        ordering = [

            "-last_used_at",

            "-created_at",

        ]



        indexes = [

            models.Index(

                fields=[

                    "user",

                    "is_active",

                ],

                name="notif_dev_user_active_idx",

            ),

            models.Index(

                fields=[

                    "provider",

                    "is_active",

                ],

                name="notif_dev_provider_idx",

            ),

            models.Index(

                fields=[

                    "platform",

                    "is_active",

                ],

                name="notif_dev_platform_idx",

            ),

            models.Index(

                fields=[

                    "user",

                    "platform",

                ],

                name="notif_dev_user_platform_idx",

            ),

            models.Index(

                fields=[

                    "user",

                    "provider",

                ],

                name="notif_dev_user_provider_idx",

            ),

        ]



    # ======================================================================

    # STRING REPRESENTATION

    # ======================================================================



    def __str__(self) -> str:

        return (

            f"{self.user} - "

            f"{self.platform}/{self.provider}"

        )



    # ======================================================================

    # STATE PROPERTIES

    # ======================================================================



    @property

    def can_receive_notifications(self) -> bool:

        """

        Return True when this device is currently eligible

        for push notification delivery.

        """



        return bool(

            self.is_active

            and self.notifications_enabled

            and self.device_token

            and self.provider

        )



    @property

    def is_available(self) -> bool:

        """

        Alias for can_receive_notifications.



        Useful for application code that wants to check

        general device availability.

        """



        return self.can_receive_notifications



    @property

    def has_token(self) -> bool:

        """

        Return True when a usable device token exists.

        """



        return bool(

            self.device_token

            and self.device_token.strip()

        )



    @property

    def has_provider(self) -> bool:

        """

        Return True when a provider has been configured.

        """



        return bool(

            self.provider

            and self.provider.strip()

        )



    # ======================================================================

    # DEVICE ACTIVITY

    # ======================================================================



    def touch(self, *, save: bool = True) -> None:

        """

        Update the device's last-used timestamp.



        Used when the client registers, refreshes, or actively

        uses the notification token.

        """



        self.last_used_at = timezone.now()



        if save:

            self.save(

                update_fields=[

                    "last_used_at",

                    "updated_at",

                ]

            )



    # ======================================================================

    # ACTIVATION

    # ======================================================================



    def activate(self) -> None:

        """

        Reactivate a previously disabled device.

        """



        self.is_active = True

        self.last_error = ""

        self.last_used_at = timezone.now()



        self.save(

            update_fields=[

                "is_active",

                "last_error",

                "last_used_at",

                "updated_at",

            ]

        )



    def deactivate(

        self,

        error_message: str = "",

    ) -> None:

        """

        Permanently disable this device for delivery.



        Typical reasons include:



            - logout

            - token invalidation

            - application uninstall

            - permanent provider error

        """



        self.is_active = False



        if error_message:

            self.last_error = str(error_message)[:5000]



        self.save(

            update_fields=[

                "is_active",

                "last_error",

                "updated_at",

            ]

        )



    # ======================================================================

    # NOTIFICATION ENABLE/DISABLE

    # ======================================================================



    def disable_notifications(self) -> None:

        """

        Disable push notifications for this device without

        deleting or deactivating the device registration.

        """



        self.notifications_enabled = False



        self.save(

            update_fields=[

                "notifications_enabled",

                "updated_at",

            ]

        )



    def enable_notifications(self) -> None:

        """

        Re-enable push notifications for this device.

        """



        self.notifications_enabled = True

        self.is_active = True

        self.last_error = ""

        self.last_used_at = timezone.now()



        self.save(

            update_fields=[

                "notifications_enabled",

                "is_active",

                "last_error",

                "last_used_at",

                "updated_at",

            ]

        )



    # ======================================================================

    # ERROR STATE

    # ======================================================================



    def set_error(

        self,

        error_message: str,

    ) -> None:

        """

        Store the most recent provider/device error.



        This does not automatically deactivate the device because

        transient provider failures should not disable a valid token.

        """



        self.last_error = str(error_message)[:5000]



        self.save(

            update_fields=[

                "last_error",

                "updated_at",

            ]

        )



    def clear_error(self) -> None:

        """

        Clear the most recent device error.

        """



        if not self.last_error:

            return



        self.last_error = ""



        self.save(

            update_fields=[

                "last_error",

                "updated_at",

            ]

        )