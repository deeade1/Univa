# apps/backend/backend/celerybeat.py

"""
Central Celery Beat schedule for Univa.

This module contains periodic schedules only.
The Celery application itself lives in backend.celery.
"""

from celery.schedules import crontab


BEAT_SCHEDULE = {

    # ========================================================================
    # TRANSPORT
    # ========================================================================

    "dispatch-transport-requests": {
        "task": "transport.tasks.batch_dispatch_requests",
        "schedule": 30.0,
        "options": {
            "queue": "transport",
        },
    },

    "run-dispatcher-every-5min": {
        "task": "transport.tasks.run_dispatcher",
        "schedule": 300.0,
        "options": {
            "queue": "transport",
        },
    },


    # ========================================================================
    # CHAT
    # ========================================================================

    "process-chat-messages": {
        "task": "chat.tasks.process_chat_queue",
        "schedule": 10.0,
        "options": {
            "queue": "chat",
        },
    },


    # ========================================================================
    # ORDERS
    # ========================================================================

    "process-pending-orders": {
        "task": "order.tasks.process_pending_orders",
        "schedule": crontab(
            minute="*/5",
        ),
        "options": {
            "queue": "order",
        },
    },


    # ========================================================================
    # REAL ESTATE
    # ========================================================================

    "check-property-updates": {
        "task": "realestate.tasks.check_property_updates",
        "schedule": crontab(
            hour="*/2",
        ),
        "options": {
            "queue": "realestate",
        },
    },


    # ========================================================================
    # NOTIFICATIONS
    # ========================================================================

    "process-notification-queue": {
        "task": "notifications.tasks.process_notification_queue",
        "schedule": 60.0,
        "options": {
            "queue": "notifications",
        },
    },

    "process-pending-notifications": {
        "task": "notifications.tasks.process_pending_notifications",
        "schedule": 300.0,
        "options": {
            "queue": "notifications",
        },
    },

    "retry-failed-notifications": {
        "task": "notifications.tasks.retry_failed_notifications",
        "schedule": 300.0,
        "options": {
            "queue": "notifications",
        },
    },

    "cleanup-stale-notification-devices": {
        "task": "notifications.tasks.cleanup_stale_devices",
        "schedule": crontab(
            hour=3,
            minute=0,
        ),
        "options": {
            "queue": "notifications",
        },
    },

    "cleanup-old-notifications": {
        "task": "notifications.tasks.cleanup_old_notifications",
        "schedule": crontab(
            hour=3,
            minute=30,
        ),
        "options": {
            "queue": "notifications",
        },
    },

    "cleanup-old-notification-events": {
        "task": "notifications.tasks.cleanup_old_events",
        "schedule": crontab(
            hour=4,
            minute=0,
        ),
        "options": {
            "queue": "notifications",
        },
    },


    # ========================================================================
    # BANKING
    # ========================================================================

    "check-fraud-every-hour": {
        "task": "banking.tasks.check_fraudulent_activity",
        "schedule": crontab(
            minute=0,
        ),
        "options": {
            "queue": "banking",
        },
    },

    "generate-monthly-statements": {
        "task": "banking.tasks.generate_monthly_statements",
        "schedule": crontab(
            day_of_month=1,
            hour=2,
            minute=0,
        ),
        "options": {
            "queue": "banking",
        },
    },


    # ========================================================================
    # COMMUNITY
    # ========================================================================

    "recompute-video-vectors-every-30min": {
        "task": "community.tasks.recompute_video_vectors",
        "schedule": crontab(
            minute="*/30",
        ),
        "args": [200],
        "options": {
            "queue": "community",
        },
    },

    "update-viral-scores-every-5min": {
        "task": "community.tasks.update_video_viral_scores",
        "schedule": crontab(
            minute="*/5",
        ),
        "args": [500],
        "options": {
            "queue": "community",
        },
    },

    "recompute-user-vectors-hourly": {
        "task": "community.tasks.recompute_all_user_vectors",
        "schedule": crontab(
            minute=0,
        ),
        "options": {
            "queue": "community",
        },
    },

    "recompute-trending-feed-every-10min": {
        "task": "community.tasks.recompute_trending_feed",
        "schedule": 600.0,
        "options": {
            "queue": "community",
        },
    },
}