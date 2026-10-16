# apps/backend/invoice/apps.py

from django.apps import AppConfig


class InvoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "invoice"

    def ready(self):
        # Register signal handlers.
        from . import signals  # noqa: F401