# apps/backend/backend/celery.py

import os

from celery import Celery


# ============================================================================
# DJANGO SETTINGS
# ============================================================================
#
# Celery does NOT call django.setup() here.
#
# Django is initialized by manage.py / wsgi.py / asgi.py. When Celery
# reads settings through config_from_object, Django is already up.
#
# Calling django.setup() at module level in this file causes:
#
#     RuntimeError: populate() isn't reentrant
#
# whenever `backend/__init__.py` imports celery while Django is still
# populating its app registry (e.g. during `manage.py check`).
# ============================================================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "backend.settings.dev",
)


from django.conf import settings                    # noqa: E402
from backend.celerybeat import BEAT_SCHEDULE        # noqa: E402


# ============================================================================
# CELERY APPLICATION
# ============================================================================

app = Celery("kaz-site")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

app.autodiscover_tasks(
    lambda: settings.INSTALLED_APPS
)


# ============================================================================
# TASK ROUTING
# ============================================================================
#
# Every application gets its own queue.
#
# This keeps heavy/background work isolated and allows workers to be scaled
# independently in production.
# ============================================================================

app.conf.task_routes = {

    # ------------------------------------------------------------------------
    # AUTH / ACCOUNTS
    # ------------------------------------------------------------------------

    "accounts.tasks.*": {
        "queue": "accounts",
    },

    # ------------------------------------------------------------------------
    # CORE
    # ------------------------------------------------------------------------

    "core.tasks.*": {
        "queue": "core",
    },

    # ------------------------------------------------------------------------
    # NOTIFICATIONS
    # ------------------------------------------------------------------------

    "notifications.tasks.*": {
        "queue": "notifications",
    },

    # ------------------------------------------------------------------------
    # CHAT
    # ------------------------------------------------------------------------

    "chat.tasks.*": {
        "queue": "chat",
    },

    # ------------------------------------------------------------------------
    # CHANNEL
    # ------------------------------------------------------------------------

    "channel.tasks.*": {
        "queue": "channel",
    },

    # ------------------------------------------------------------------------
    # SOCIAL
    # ------------------------------------------------------------------------

    "social.tasks.*": {
        "queue": "social",
    },

    # ------------------------------------------------------------------------
    # COMMUNITY
    # ------------------------------------------------------------------------

    "community.tasks.*": {
        "queue": "community",
    },

    # ------------------------------------------------------------------------
    # BLOG
    # ------------------------------------------------------------------------

    "blog.tasks.*": {
        "queue": "blog",
    },

    # ------------------------------------------------------------------------
    # E-COMMERCE
    # ------------------------------------------------------------------------

    "product.tasks.*": {
        "queue": "product",
    },

    "order.tasks.*": {
        "queue": "order",
    },

    "checkout.tasks.*": {
        "queue": "checkout",
    },

    "discount.tasks.*": {
        "queue": "discount",
    },

    "giftcard.tasks.*": {
        "queue": "giftcard",
    },

    # ------------------------------------------------------------------------
    # E-COMMERCE — INTERNAL APP PACKAGE (ecommerce.tasks.*)
    #
    # Tasks that live under the `ecommerce` app package. Routed to the
    # same queue as their domain equivalents so a worker started with
    # `-Q payment,checkout,...` consumes them.
    # ------------------------------------------------------------------------

    "ecommerce.tasks.payment.*": {
        "queue": "payment",
    },

    "ecommerce.tasks.checkout.*": {
        "queue": "checkout",
    },

    # ------------------------------------------------------------------------
    # SHIPPING / WAREHOUSE
    # ------------------------------------------------------------------------

    "shipping.tasks.*": {
        "queue": "shipping",
    },

    "warehouse.tasks.*": {
        "queue": "warehouse",
    },

    # ------------------------------------------------------------------------
    # PAYMENT / INVOICE
    # ------------------------------------------------------------------------

    "payment.tasks.*": {
        "queue": "payment",
    },

    "invoice.tasks.*": {
        "queue": "invoice",
    },

    # ------------------------------------------------------------------------
    # BANKING
    # ------------------------------------------------------------------------

    "banking.tasks.*": {
        "queue": "banking",
    },

    # ------------------------------------------------------------------------
    # TRANSPORT
    # ------------------------------------------------------------------------

    "transport.tasks.*": {
        "queue": "transport",
    },

    # ------------------------------------------------------------------------
    # REAL ESTATE
    # ------------------------------------------------------------------------

    "realestate.tasks.*": {
        "queue": "realestate",
    },

    # ------------------------------------------------------------------------
    # TAX / SEO / CATALOG SUPPORT
    # ------------------------------------------------------------------------

    "tax.tasks.*": {
        "queue": "tax",
    },

    "seo.tasks.*": {
        "queue": "seo",
    },

    "gotomarket.tasks.*": {
        "queue": "gotomarket",
    },
}


# ============================================================================
# CELERY BEAT
# ============================================================================

app.conf.beat_schedule = BEAT_SCHEDULE


# ============================================================================
# GENERAL CELERY CONFIGURATION
# ============================================================================

app.conf.update(
    timezone="Africa/Lagos",
    enable_utc=True,

    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    task_track_started=True,

    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,

    task_acks_late=True,
    task_reject_on_worker_lost=True,

    worker_prefetch_multiplier=1,

    task_create_missing_queues=True,
)


# ============================================================================
# DEBUG TASK
# ============================================================================

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")