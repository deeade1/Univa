from django.apps import AppConfig


class PaymentCanonicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payment.canonical"
    label = "payment_canonical"