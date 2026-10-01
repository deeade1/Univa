from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=None)
def service_request_created(sender, instance, created, **kwargs):
    ServiceRequest = apps.get_model('transport', 'ServiceRequest')
    if isinstance(instance, ServiceRequest) and created:
        print(f"[Signal] New ServiceRequest created with ID: {instance.id}")

@receiver(post_save, sender=None)
def booking_created(sender, instance, created, **kwargs):
    Booking = apps.get_model('transport', 'Booking')
    if isinstance(instance, Booking) and created:
        print(f"[Signal] New Booking created for ServiceRequest #{instance.service_request.id}")
