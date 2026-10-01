# notifications/tasks/__init__.py

"""
Notification Celery task API.

This package exposes the public notification Celery tasks.

Task orchestration and retry behavior live in the individual
task modules. This initializer is what makes Celery autodiscovery
register those tasks, because Celery only imports ``notifications.tasks``
and does not walk submodules.
"""

# ---------------------------------------------------------------------------
# Push delivery
# ---------------------------------------------------------------------------

from .push import (
    deliver_notification,
    deliver_pending_push_notifications,
    deliver_push_notification,
    retry_failed_push_notifications,
)

# ---------------------------------------------------------------------------
# Delivery orchestration
# ---------------------------------------------------------------------------

from .delivery_tasks import (
    deliver_notification_push,
)

# ---------------------------------------------------------------------------
# Event processing
# ---------------------------------------------------------------------------

from .event_tasks import (
    process_notification_event_task,
    recover_stale_notification_events,
    retry_failed_notification_events,
)

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

from .email import (
    send_email_notification,
)

# ---------------------------------------------------------------------------
# In-app
# ---------------------------------------------------------------------------

from .in_app import (
    send_in_app_notification,
    send_in_app_notification_for_user,
)

# ---------------------------------------------------------------------------
# SMS
# ---------------------------------------------------------------------------

from .sms import (
    send_sms_notification,
)

# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

from .websocket import (
    send_websocket_notification,
)

# ---------------------------------------------------------------------------
# Queue processing
# ---------------------------------------------------------------------------

from .process_notification_queue import (
    process_notification_queue,
    process_notification_push,
    enqueue_pending_notification_pushes,
)

# ---------------------------------------------------------------------------
# Generic notification tasks
# ---------------------------------------------------------------------------

from .notification_tasks import (
    prepare_notification_delivery,
)

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

from .maintenance_tasks import (
    cleanup_stale_devices,
    recover_stale_notification_events,
    recover_stale_notification_pushes,
    cleanup_old_notifications,
    cleanup_old_push_deliveries,
    cleanup_old_events,
    run_notification_maintenance,
)


__all__ = [
    # push
    "deliver_push_notification",
    "deliver_pending_push_notifications",
    "retry_failed_push_notifications",
    "deliver_notification",
    "deliver_notification_push",
    # event
    "process_notification_event_task",
    "recover_stale_notification_events",
    "retry_failed_notification_events",
    # email
    "send_email_notification",
    # in-app
    "send_in_app_notification",
    "send_in_app_notification_for_user",
    # sms
    "send_sms_notification",
    # websocket
    "send_websocket_notification",
    # queue
    "process_notification_queue",
    "process_notification_push",
    "enqueue_pending_notification_pushes",
    # notification tasks
    "prepare_notification_delivery",
    # maintenance
    "cleanup_stale_devices",
    "recover_stale_notification_pushes",
    "cleanup_old_notifications",
    "cleanup_old_push_deliveries",
    "cleanup_old_events",
    "run_notification_maintenance",
]