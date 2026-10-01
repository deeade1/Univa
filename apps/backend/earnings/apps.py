# apps/backend/earnings/apps.py

from django.apps import AppConfig


class EarningsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "earnings"
    verbose_name = "Earnings"