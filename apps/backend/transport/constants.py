# transport/models/core/constants.py
"""
Shared constants for transport models.
"""

from django.utils.translation import gettext_lazy as _


class ServiceType:
    """Service type constants."""
    TAXI = 'taxi'
    DELIVERY = 'delivery'
    SHARED = 'shared'
    FOOD = 'food'
    CARGO = 'cargo'
    INTERSTATE = 'interstate'
    
    CHOICES = [
        (TAXI, _('Taxi Ride')),
        (DELIVERY, _('Package Delivery')),
        (SHARED, _('Shared Ride')),
        (FOOD, _('Food Delivery')),
        (CARGO, _('Cargo Transport')),
        (INTERSTATE, _('Interstate Travel')),
    ]


class ServiceStatus:
    """Service request status constants."""
    REQUESTED = 'requested'
    ACCEPTED = 'accepted'
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    DEPARTED = 'departed'
    IN_TRANSIT = 'in_transit'
    ARRIVED = 'arrived'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (REQUESTED, _('Requested')),
        (ACCEPTED, _('Accepted')),
        (SCHEDULED, _('Scheduled')),
        (IN_PROGRESS, _('In Progress')),
        (DEPARTED, _('Departed')),
        (IN_TRANSIT, _('In Transit')),
        (ARRIVED, _('Arrived')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
    ]


class PackageStatus:
    """Package status constants."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    READY_FOR_PICKUP = 'ready_for_pickup'
    PICKED_UP = 'picked_up'
    IN_TRANSIT = 'in_transit'
    OUT_FOR_DELIVERY = 'out_for_delivery'
    DELIVERY_ATTEMPTED = 'delivery_attempted'
    DELIVERED = 'delivered'
    EXCEPTION = 'exception'
    RETURNED = 'returned'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PENDING, _('Pending')),
        (PROCESSING, _('Processing')),
        (READY_FOR_PICKUP, _('Ready for Pickup')),
        (PICKED_UP, _('Picked Up')),
        (IN_TRANSIT, _('In Transit')),
        (OUT_FOR_DELIVERY, _('Out for Delivery')),
        (DELIVERY_ATTEMPTED, _('Delivery Attempted')),
        (DELIVERED, _('Delivered')),
        (EXCEPTION, _('Exception')),
        (RETURNED, _('Returned')),
        (CANCELLED, _('Cancelled')),
    ]


class ProviderType:
    """Provider type constants."""
    DRIVER = 'driver'
    COURIER = 'courier'
    RIDER = 'rider'
    
    CHOICES = [
        (DRIVER, _('Driver')),
        (COURIER, _('Courier')),
        (RIDER, _('Rider')),
    ]


class TrackingPriority:
    """Tracking priority constants."""
    STANDARD = 'standard'
    EXPRESS = 'express'
    PRIORITY = 'priority'
    SAME_DAY = 'same_day'
    
    CHOICES = [
        (STANDARD, _('Standard')),
        (EXPRESS, _('Express')),
        (PRIORITY, _('Priority')),
        (SAME_DAY, _('Same Day')),
    ]