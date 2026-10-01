from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from leaflet.admin import LeafletGeoAdmin
from django.contrib.admin import SimpleListFilter
from django.urls import reverse
from django.db.models import Avg, Count, Sum
from django.core.exceptions import ValidationError
from .models.shared.analytics import  AnalyticsProfile, RideMetrics, KPI
from .models.rating import Rating, CustomerRating, ProviderRating
from .models.core.service_provider import ServiceProviderProfile
from .models.core.service_request import ServiceRequest
from .models.delivery.delivery import Delivery


from .models.delivery.logistics import StopPoint
from .models.delivery.tracking import Tracking, TrackingEvent
from .models.financial.cancellation import (CancellationPolicy,
                                            CancellationRecord)
from .models.financial.earnings import DriverEarning, IncentiveProgram
from .models.maintenance.maintenance_schedule import (MaintenanceLog,
                                                      MaintenanceSchedule)
from .models.maintenance.telemetry import PredictiveAlert, VehicleTelemetry
from .models.maintenance.vehicle import Vehicle
from .models.maintenance.vehicle_inspection import VehicleInspection
from .models.rides.boarding import BoardingTicket
from .models.rides.booking import Booking
from .models.rides.schedule import TripScheduleTemplate
from .models.rides.shared_trip import (
    SharedTrip, 
    WaitlistEntry, 
    UserPreference
)
from .models.rides.trip import Trip
from .models.shared.realtime import (
    EmergencyAlert, 
    RealTimeTracking,
    TrafficConditions
    )

from transport.models import (
    RouteStop,
)




# -------------------- BOARDING TICKET ADMIN ---------------------

@admin.register(BoardingTicket)
class BoardingTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "user", "booking", "redeemed", "created_at", "redeemed_at", "qr_preview")
    search_fields = ("id", "user__email", "trip__id", "booking__id")
    list_filter = ("redeemed", "created_at")
    readonly_fields = ("qr_image", "qr_preview", "created_at", "redeemed_at")

    def qr_preview(self, obj):
        if obj.qr_image:
            return format_html(f'<img src="{obj.qr_image.url}" width="120" />')
        return "No QR"
    qr_preview.short_description = "QR Code"

    @admin.action(description="Mark selected tickets as redeemed")
    def mark_redeemed(self, request, queryset):
        queryset.update(redeemed=True, redeemed_at=timezone.now())


# -------------------- BOOKING ADMIN ---------------------

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "service_request", "user", "status", "booked_at")
    list_filter = ("status", "booked_at")
    search_fields = ("id", "user__email", "service_request__id")
    readonly_fields = ("booked_at",)
    ordering = ("-booked_at",)


# -------------------- SHARED TRIP ADMIN ---------------------



@admin.register(SharedTrip)
class SharedTripAdmin(admin.ModelAdmin):
    """Admin for SharedTrip (proxy model)."""
    
    list_display = (
        "id",
        "customer",
        "shared_available_seats_display",
        "shared_status_display",
        "shared_day_time_display",
        "created_at",
    )
    
    list_filter = (
        "status",  # Use actual model field 'status' from ServiceRequest
        "service_type",
        "created_at",
    )
    
    search_fields = (
        "customer__email",
        "customer__first_name",
        "customer__last_name",
    )
    
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    
    def shared_available_seats_display(self, obj):
        """Display available seats from JSON field."""
        return obj.shared_available_seats
    shared_available_seats_display.short_description = "Available Seats"
    
    def shared_status_display(self, obj):
        """Display shared status from JSON field."""
        return obj.shared_status_display
    shared_status_display.short_description = "Shared Status"
    
    def shared_day_time_display(self, obj):
        """Display day/time from JSON field."""
        return obj.day_time_display
    shared_day_time_display.short_description = "Day/Time"



@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    """Admin for EmergencyAlert."""

    list_display = (
        "id",
        "title",
        "alert_type",
        "severity",
        "status_display",
        "created_at",
    )

    list_filter = (
        "alert_type",
        "severity",
        "status",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "location_description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    raw_id_fields = (
        "service_request",
        "reported_by",
    )

    def status_display(self, obj):
        """Display status."""
        return obj.get_status_display()

    status_display.short_description = "Status"


@admin.register(RealTimeTracking)
class RealTimeTrackingAdmin(GISModelAdmin):
    """Admin for RealTimeTracking."""

    list_display = (
        "id",
        "vehicle",
        "speed",
        "is_moving",
        "timestamp",
    )

    list_filter = (
        "platform",
        "is_moving",
        "timestamp",
    )

    search_fields = (
        "vehicle__name",
        "vehicle__license_plate",
        "device_id",
    )

    readonly_fields = (
        "timestamp",
    )

    raw_id_fields = (
        "vehicle",
        "service_request",
    )


@admin.register(TrafficConditions)
class TrafficConditionsAdmin(GISModelAdmin):
    """Admin for TrafficConditions."""

    list_display = (
        "id",
        "road_name",
        "traffic_level",
        "average_speed",
        "is_valid_display",
        "recorded_at",
    )

    list_filter = (
        "traffic_level",
        "source",
        "recorded_at",
    )

    search_fields = (
        "road_name",
    )

    readonly_fields = (
        "recorded_at",
    )

    def is_valid_display(self, obj):
        """Display if traffic data is still valid."""
        return obj.is_valid

    is_valid_display.short_description = "Valid"
    is_valid_display.boolean = True


@admin.register(Tracking)
class TrackingAdmin(admin.ModelAdmin):
    """Admin for Tracking."""

    list_display = (
        "id",
        "tracking_number",
        "current_status",
        "is_delivered_display",
        "package",
        "delivery",
        "created_at",
    )

    list_filter = (
        "current_status",
        "priority",
        "created_at",
    )

    search_fields = (
        "tracking_number",
        "carrier_tracking_number",
        "carrier_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    raw_id_fields = (
        "package",
        "delivery",
        "service_request",
    )

    def is_delivered_display(self, obj):
        """Display if delivered."""
        return obj.is_delivered

    is_delivered_display.short_description = "Delivered"
    is_delivered_display.boolean = True



@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    """Admin for RouteStop."""
    
    list_display = (
        "id",
        "route",
        "stop",
        "order",
        
    )
    
    list_filter = (
        "route",
        "order",
    )
    
    search_fields = (
        "stop__name",
        "stop__location",
    )
    
    
    raw_id_fields = (
        "route",
        "stop",
    )


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    """Admin for WaitlistEntry."""
    
    list_display = (
        "id",
        "shared_trip",
        "user",
        "position",
        "notified",
        "expired",
        "joined_at",
    )
    
    list_filter = (
        "notified",
        "expired",
        "joined_at",
    )
    
    search_fields = (
        "user__email",
        "shared_trip__id",
    )
    
    readonly_fields = (
        "joined_at",
        "created_at",
        "updated_at",
    )
    
    raw_id_fields = (
        "shared_trip",
        "user",
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin for UserPreference."""
    
    list_display = (
        "id",
        "user",
        "music_preference",
        "conversation_level",
        "temperature_preference",
        "created_at",
    )
    
    list_filter = (
        "music_preference",
        "conversation_level",
        "temperature_preference",
    )
    
    search_fields = (
        "user__email",
    )
    
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    
    raw_id_fields = (
        "user",
    )


# -------------------- SCHEDULE TEMPLATE ADMIN ---------------------

@admin.register(TripScheduleTemplate)
class TripScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ("route_name", "departure_city", "destination_city", "departure_time", "active")
    search_fields = ("route_name", "departure_city", "destination_city")
    list_filter = ("active",)
    ordering = ("-created_at",)


# -------------------- TRIP ADMIN ---------------------




@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_package_type', 'get_weight_kg', 'get_cancelled')
    search_fields = ('delivery_data',)
    list_filter = ('status',)  # Use actual field instead of cancelled
    
    # Custom methods to display JSON data
    def get_package_type(self, obj):
        return obj.delivery_data.get('package_type', '')
    get_package_type.short_description = 'Package Type'
    get_package_type.admin_order_field = 'delivery_data__package_type'
    
    def get_weight_kg(self, obj):
        return obj.delivery_data.get('weight_kg', 0.0)
    get_weight_kg.short_description = 'Weight (kg)'
    get_weight_kg.admin_order_field = 'delivery_data__weight_kg'
    
    def get_cancelled(self, obj):
        return obj.delivery_data.get('cancelled', False)
    get_cancelled.short_description = 'Cancelled'
    get_cancelled.admin_order_field = 'delivery_data__cancelled'
    
    # Custom filter for cancelled
    class DeliveryCancelledFilter(admin.SimpleListFilter):
        title = 'cancelled'
        parameter_name = 'cancelled'
        
        def lookups(self, request, model_admin):
            return (
                ('true', 'Cancelled'),
                ('false', 'Not Cancelled'),
            )
        
        def queryset(self, request, queryset):
            if self.value() == 'true':
                return queryset.filter(delivery_data__cancelled=True)
            elif self.value() == 'false':
                return queryset.filter(delivery_data__cancelled=False)
            return queryset
    
    list_filter = (DeliveryCancelledFilter, 'status')

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_shared',
        'get_available_seats',
        'get_rider_count',
        'get_cancelled',
        'get_day_time',
        'get_surge_multiplier',
    )
    
    # Custom filters
    class TripSharedFilter(admin.SimpleListFilter):
        title = 'shared'
        parameter_name = 'shared'
        
        def lookups(self, request, model_admin):
            return (
                ('true', 'Shared'),
                ('false', 'Not Shared'),
            )
        
        def queryset(self, request, queryset):
            if self.value() == 'true':
                return queryset.filter(trip_data__shared=True)
            elif self.value() == 'false':
                return queryset.filter(trip_data__shared=False)
            return queryset
    
    class TripCancelledFilter(admin.SimpleListFilter):
        title = 'cancelled'
        parameter_name = 'cancelled'
        
        def lookups(self, request, model_admin):
            return (
                ('true', 'Cancelled'),
                ('false', 'Not Cancelled'),
            )
        
        def queryset(self, request, queryset):
            if self.value() == 'true':
                return queryset.filter(trip_data__cancelled=True)
            elif self.value() == 'false':
                return queryset.filter(trip_data__cancelled=False)
            return queryset
    
    class TripDayTimeFilter(admin.SimpleListFilter):
        title = 'day_time'
        parameter_name = 'day_time'
        
        def lookups(self, request, model_admin):
            # Extract unique values from trip_data
            trips = Trip.objects.all()
            day_times = set()
            for trip in trips:
                day_time = trip.trip_data.get('day_time')
                if day_time:
                    day_times.add((day_time, day_time.capitalize()))
            return sorted(day_times)
        
        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(trip_data__day_time=self.value())
            return queryset
    
    list_filter = (
        TripSharedFilter,
        TripCancelledFilter,
        TripDayTimeFilter,
        'status',
    )
    
    search_fields = ('id', 'trip_data__special_requests')
    ordering = ('-id',)
    readonly_fields = ('get_trip_data_display',)
    
    # Custom display methods
    def get_shared(self, obj):
        return obj.trip_data.get('shared', False)
    get_shared.short_description = 'Shared'
    get_shared.boolean = True
    get_shared.admin_order_field = 'trip_data__shared'
    
    def get_available_seats(self, obj):
        return obj.trip_data.get('available_seats', 1)
    get_available_seats.short_description = 'Available Seats'
    get_available_seats.admin_order_field = 'trip_data__available_seats'
    
    def get_rider_count(self, obj):
        return obj.trip_data.get('rider_count', 1)
    get_rider_count.short_description = 'Rider Count'
    get_rider_count.admin_order_field = 'trip_data__rider_count'
    
    def get_cancelled(self, obj):
        return obj.trip_data.get('cancelled', False)
    get_cancelled.short_description = 'Cancelled'
    get_cancelled.boolean = True
    get_cancelled.admin_order_field = 'trip_data__cancelled'
    
    def get_day_time(self, obj):
        return obj.trip_data.get('day_time', 'day').capitalize()
    get_day_time.short_description = 'Day/Time'
    get_day_time.admin_order_field = 'trip_data__day_time'
    
    def get_surge_multiplier(self, obj):
        return obj.trip_data.get('surge_multiplier', 1.0)
    get_surge_multiplier.short_description = 'Surge'
    get_surge_multiplier.admin_order_field = 'trip_data__surge_multiplier'
    
    def get_special_requests(self, obj):
        return obj.trip_data.get('special_requests', '')
    get_special_requests.short_description = 'Special Requests'
    
    def get_cancellation_reason(self, obj):
        return obj.trip_data.get('cancellation_reason', '')
    get_cancellation_reason.short_description = 'Cancellation Reason'
    
    def get_safety_incidents(self, obj):
        return obj.trip_data.get('safety_incidents', 0)
    get_safety_incidents.short_description = 'Safety Incidents'
    
    def get_trip_data_display(self, obj):
        """Display formatted trip data"""
        import json
        return json.dumps(obj.trip_data, indent=2)
    get_trip_data_display.short_description = 'Trip Data (JSON)'
    
    fieldsets = (
        (None, {
            'fields': ('customer', 'vehicle')
        }),
        ('Trip Details', {
            'fields': (
                'get_shared',
                'get_available_seats', 
                'get_rider_count', 
                'get_special_requests', 
                'get_day_time', 
                'get_surge_multiplier'
            )
        }),
        ('Status', {
            'fields': (
                'get_cancelled', 
                'get_cancellation_reason', 
                'get_safety_incidents'
            ),
        }),
        ('Raw Data', {
            'fields': ('get_trip_data_display',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['cancel_selected_trips']
    
    def cancel_selected_trips(self, request, queryset):
        """Admin action to cancel multiple trips"""
        for trip in queryset:
            trip_data = trip.trip_data.copy()
            trip_data['cancelled'] = True
            trip_data['cancellation_reason'] = "Cancelled by admin"
            trip.trip_data = trip_data
            trip.save(update_fields=['trip_data'])
        self.message_user(request, f"{queryset.count()} trips cancelled.")
    cancel_selected_trips.short_description = "Cancel selected trips"

@admin.register(ServiceProviderProfile)
class ServiceProviderProfileAdmin(LeafletGeoAdmin):
    list_display = (
        "id", "user", "provider_type", "is_available", "is_online",
        "rating", "verified_union_member", "last_active"
    )
    list_filter = (
        "provider_type", "is_available", "is_online",
        "verified_union_member"
    )
    search_fields = ("user__email", "license_number", "union_id")
    ordering = ("-last_active",)
    readonly_fields = ("last_active",)

    fieldsets = (
        ("Basic Info", {
            "fields": ("user", "provider_type", "is_available", "is_online")
        }),
        ("License & Verification", {
            "fields": (
                "license_number", "license_type",
                "union_id", "verified_union_member",
                "insurance_policy_number", "insurance_provider"
            )
        }),
        ("Emergency Contact", {
            "fields": ("emergency_contact_name", "emergency_contact_phone")
        }),
        ("Location", {
            "fields": ("location_point", "address")
        }),
        ("Performance", {
            "fields": ("rating", "last_active")
        }),
        ("Vehicle Eligibility", {
            "fields": ("allowed_vehicle_types",)
        }),
    )

@admin.register(ServiceRequest)
class ServiceRequestAdmin(LeafletGeoAdmin):
    list_display = (
        "id", "service_type", "status", "customer",
        "provider", "created_at", "estimated_arrival_time",
        "total_fare"
    )
    list_filter = (
        "service_type", "status",
        "insurance_required", "is_recurring_daily",
        "departure_state", "destination_state"
    )
    search_fields = (
        "id", "customer__email", "provider__user__email",
        "departure_city", "destination_city"
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "started_at", "completed_at")

    fieldsets = (
        ("Basic Info", {
            "fields": ("service_type", "status", "customer", "provider", "vehicle")
        }),
        ("Locations", {
            "fields": (
                "pickup_location", "pickup_address",
                "dropoff_location", "dropoff_address"
            )
        }),
        ("Interstate Travel", {
            "fields": (
                "departure_state", "departure_city", "departure_terminal",
                "destination_state", "destination_city", "destination_terminal",
                "route", "estimated_distance", "estimated_duration"
            )
        }),
        ("Scheduling", {
            "fields": ("estimated_arrival_time", "is_recurring_daily")
        }),
        ("Trip Pricing", {
            "fields": (
                "base_fare", "distance_fare", "time_fare",
                "luggage_capacity_kg", "luggage_price_per_kg",
                "total_fare"
            )
        }),
        ("Ratings", {
            "fields": ("customer_rating", "provider_rating")
        }),
        ("Insurance & Safety", {
            "fields": ("insurance_required", "insurance_details",
                       "emergency_contact_name", "emergency_contact_phone")
        }),
        ("Timestamps", {
            "fields": ("created_at", "started_at", "completed_at")
        }),
    )


class StopPointInline(LeafletGeoAdmin, admin.TabularInline):
    model = StopPoint
    extra = 1
    fields = ("sequence", "location", "address", "is_pickup", "is_dropoff")
    ordering = ("sequence",)



class TrackingEventInline(LeafletGeoAdmin, admin.TabularInline):
    model = TrackingEvent
    extra = 0
    readonly_fields = ("timestamp",)
    fields = ("status", "description", "location", "coordinates", "timestamp")


@admin.register(TrackingEvent)
class TrackingEventAdmin(LeafletGeoAdmin):
    list_display = ("tracking", "status", "location", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("tracking__tracking_number", "location")
    ordering = ("-timestamp",)


@admin.register(CancellationPolicy)
class CancellationPolicyAdmin(admin.ModelAdmin):
    list_display = (
        'service_type', 'name', 'free_cancellation_minutes',
        'cancellation_fee', 'refund_percentage', 'is_active'
    )
    list_filter = ('service_type', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('service_type',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CancellationRecord)
class CancellationRecordAdmin(admin.ModelAdmin):
    list_display = (
        'service_request', 'cancelled_by', 'cancellation_party',
        'reason', 'cancelled_at', 'penalty_applied'
    )
    list_filter = ('cancellation_party', 'reason', 'penalty_applied')
    search_fields = ('service_request__id', 'cancelled_by__email')
    readonly_fields = (
        'service_request', 'cancelled_by', 'cancellation_party',
        'reason', 'minutes_after_acceptance', 'ride_fare',
        'cancellation_fee', 'refund_amount', 'driver_compensation',
        'policy', 'penalty_applied', 'penalty_details', 'created_at'
    )
    ordering = ('-cancelled_at',)

@admin.register(DriverEarning)
class DriverEarningAdmin(admin.ModelAdmin):
    list_display = (
        'driver', 'period', 'period_start', 'period_end',
        'total_earnings', 'net_earnings', 'payout_status'
    )
    list_filter = ('period', 'payout_status')
    search_fields = ('driver__user__email',)
    readonly_fields = ('total_earnings', 'net_earnings', 'payout_amount', 'created_at', 'updated_at')
    ordering = ('-period_start',)

    actions = ['mark_paid']

    def mark_paid(self, request, queryset):
        for earning in queryset:
            earning.payout_status = DriverEarning.PayoutStatus.PAID
            earning.paid_at = timezone.now()
            earning.save(update_fields=['payout_status', 'paid_at'])
        self.message_user(request, _("Selected earnings marked as Paid"))

    mark_paid.short_description = _("Mark selected earnings as Paid")

@admin.register(IncentiveProgram)
class IncentiveProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'incentive_type', 'reward_amount', 'reward_type', 'is_active', 'start_date', 'end_date')
    list_filter = ('incentive_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-start_date',)



@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "category", "vehicle_type", "license_plate",
        "owner", "is_active", "is_moving", "created_at"
    )
    list_filter = ("category", "vehicle_type", "is_active", "is_moving", "created_at")
    search_fields = ("license_plate", "make", "model", "owner__user__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_location_update")

    fieldsets = (
        (_("Vehicle Info"), {"fields": ("owner", "category", "vehicle_type", "make", "model", "year", "color")}),
        (_("Specs & Capacity"), {"fields": ("passenger_capacity", "cargo_capacity")}),
        (_("Registration"), {"fields": ("license_plate",)}),
        (_("Status & Tracking"), {"fields": ("is_active", "is_moving", "current_provider", "last_location_update")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )


class MaintenanceLogInline(admin.TabularInline):
    model = MaintenanceLog
    extra = 0
    readonly_fields = ("log_date", "description", "log_type", "cost", "mileage")
    can_delete = False


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle", "maintenance_type", "status",
        "scheduled_date", "is_overdue", "is_urgent", "is_recurring"
    )
    list_filter = ("maintenance_type", "status", "is_overdue", "is_urgent", "is_recurring")
    search_fields = ("vehicle__license_plate", "description")
    ordering = ("scheduled_date",)
    readonly_fields = ("created_at", "updated_at")

    inlines = [MaintenanceLogInline]

    actions = ["mark_completed"]

    @admin.action(description=_("Mark selected maintenance schedules as completed"))
    def mark_completed(self, request, queryset):
        queryset.update(status=MaintenanceSchedule.Status.COMPLETED, completed_date=timezone.now())
        self.message_user(request, _("Selected maintenance marked completed"))


@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "log_date", "log_type", "title", "mileage", "cost", "is_verified")
    list_filter = ("log_type", "is_verified", "service_provider")
    search_fields = ("vehicle__license_plate", "title", "description")
    ordering = ("-log_date",)
    readonly_fields = ("created_at",)

@admin.register(VehicleInspection)
class VehicleInspectionAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "inspection_type",  "inspection_date", "next_inspection_date")
    list_filter = ("inspection_type",  "inspection_date")
    search_fields = ("vehicle__license_plate", "inspected_by__user__email")
    ordering = ("-inspection_date",)
    readonly_fields = ("inspection_date",)

@admin.register(VehicleTelemetry)
class VehicleTelemetryAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "odometer_reading", "fuel_level", "engine_temperature", "battery_voltage", "recorded_at")
    list_filter = ("recorded_at",)
    search_fields = ("vehicle__license_plate",)
    ordering = ("-recorded_at",)

@admin.register(PredictiveAlert)
class PredictiveAlertAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "alert_type", "severity", "title", "confidence_score", "is_resolved", "created_at")
    list_filter = ("severity", "alert_type", "is_resolved")
    search_fields = ("vehicle__license_plate", "title", "description", "predicted_issue")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")



# ============ FILTERS ============
class ScoreFilter(SimpleListFilter):
    title = 'rating score'
    parameter_name = 'score'

    def lookups(self, request, model_admin):
        return (
            ('high', 'High (4-5)'),
            ('medium', 'Medium (3)'),
            ('low', 'Low (1-2)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(score__in=[4, 5])
        if self.value() == 'medium':
            return queryset.filter(score=3)
        if self.value() == 'low':
            return queryset.filter(score__in=[1, 2])
        return queryset


class ReportFrequencyFilter(SimpleListFilter):
    title = 'report frequency'
    parameter_name = 'frequency'

    def lookups(self, request, model_admin):
        return [
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(report_frequency=self.value())
        return queryset


class KPICategoryFilter(SimpleListFilter):
    title = 'KPI category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return [
            ('environmental', 'Environmental'),
            ('financial', 'Financial'),
            ('operational', 'Operational'),
            ('customer', 'Customer Satisfaction'),
            ('safety', 'Safety'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category=self.value())
        return queryset


class ComfortScoreFilter(SimpleListFilter):
    title = 'comfort score'
    parameter_name = 'comfort'

    def lookups(self, request, model_admin):
        return (
            ('excellent', 'Excellent (4-5)'),
            ('good', 'Good (3-4)'),
            ('poor', 'Poor (0-2)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'excellent':
            return queryset.filter(passenger_comfort_score__gte=4)
        if self.value() == 'good':
            return queryset.filter(passenger_comfort_score__range=[3, 4])
        if self.value() == 'poor':
            return queryset.filter(passenger_comfort_score__lte=2)
        return queryset



@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = [
        'rater_email', 'rated_user_email', 'trip_id', 'score_stars', 
        'comment_preview', 'created_at'
    ]
    list_filter = ['score', ScoreFilter, 'created_at']
    search_fields = [
        'rater__email', 'rated_user__email', 'trip__id', 
        'comment'
    ]
    readonly_fields = ['created_at']
    fieldsets = [
        ('Rating Participants', {
            'fields': ['rater', 'rated_user', 'trip']
        }),
        ('Rating Details', {
            'fields': ['score', 'comment']
        }),
        ('Metadata', {
            'fields': ['created_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['recalculate_user_ratings']

    def rater_email(self, obj):
        return obj.rater.email
    rater_email.short_description = 'Rater'
    rater_email.admin_order_field = 'rater__email'

    def rated_user_email(self, obj):
        return obj.rated_user.email
    rated_user_email.short_description = 'Rated User'
    rated_user_email.admin_order_field = 'rated_user__email'

    def trip_id(self, obj):
        return f"Trip #{obj.trip.id}"
    trip_id.short_description = 'Trip'
    trip_id.admin_order_field = 'trip__id'

    def score_stars(self, obj):
        return '★' * obj.score + '☆' * (5 - obj.score)
    score_stars.short_description = 'Score'

    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return "No comment"
    comment_preview.short_description = 'Comment'

    def recalculate_user_ratings(self, request, queryset):
        """Recalculate average ratings for affected users"""
        from django.db.models import Avg
        
        rated_users = set(queryset.values_list('rated_user', flat=True))
        
        for user_id in rated_users:
            avg_rating = Rating.objects.filter(
                rated_user_id=user_id
            ).aggregate(avg_score=Avg('score'))['avg_score']
            
            # Update user profile with new average rating
            from accounts.models import UserProfile
            UserProfile.objects.filter(id=user_id).update(
                average_rating=avg_rating
            )
        
        self.message_user(
            request, 
            f"Recalculated ratings for {len(rated_users)} users"
        )
    recalculate_user_ratings.short_description = "Recalculate user average ratings"


@admin.register(AnalyticsProfile)
class AnalyticsProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'track_ride_metrics', 'track_environmental_impact',
        'track_cost_savings', 'report_frequency', 'updated_at'
    ]
    list_filter = [
        'track_ride_metrics', 'track_environmental_impact', 
        'track_cost_savings', 'track_accessibility_usage',
        'share_aggregate_data', 'share_for_research',
        ReportFrequencyFilter
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('User', {
            'fields': ['user']
        }),
        ('Tracking Preferences', {
            'fields': [
                'track_ride_metrics',
                'track_environmental_impact', 
                'track_cost_savings',
                'track_accessibility_usage'
            ]
        }),
        ('Reporting Preferences', {
            'fields': ['report_frequency']
        }),
        ('Data Sharing', {
            'fields': ['share_aggregate_data', 'share_for_research'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'


@admin.register(RideMetrics)
class RideMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'ride_id', 'distance_km', 'duration_minutes', 'average_speed_kmh',
        'co2_emissions_kg', 'operational_cost', 'comfort_score_display',
        'created_at'
    ]
    list_filter = [ComfortScoreFilter, 'created_at']
    search_fields = ['ride__id', 'ride__route__name']
    readonly_fields = ['created_at']
    fieldsets = [
        ('Ride Information', {
            'fields': ['ride']
        }),
        ('Performance Metrics', {
            'fields': [
                'distance_km', 'duration_minutes', 'average_speed_kmh',
                'fuel_consumption_liters', 'energy_consumption_kwh'
            ]
        }),
        ('Environmental Metrics', {
            'fields': [
                'co2_emissions_kg', 'particulate_matter_emissions'
            ],
            'classes': ['collapse']
        }),
        ('Cost Metrics', {
            'fields': ['operational_cost', 'maintenance_cost_share'],
            'classes': ['collapse']
        }),
        ('Quality Metrics', {
            'fields': ['passenger_comfort_score', 'accessibility_score'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['calculate_environmental_impact', 'generate_metrics_report']

    def ride_id(self, obj):
        return f"Ride #{obj.ride.id}"
    ride_id.short_description = 'Ride'
    ride_id.admin_order_field = 'ride__id'

    def comfort_score_display(self, obj):
        if obj.passenger_comfort_score:
            return f"{obj.passenger_comfort_score:.1f}/5.0"
        return "N/A"
    comfort_score_display.short_description = 'Comfort Score'

    def calculate_environmental_impact(self, request, queryset):
        """Recalculate environmental impact for selected rides"""
        updated_count = 0
        for metric in queryset:
            # Simple calculation example - replace with your actual logic
            if metric.distance_km and not metric.co2_emissions_kg:
                metric.co2_emissions_kg = metric.distance_km * 0.12  # Example factor
                metric.save()
                updated_count += 1
        
        self.message_user(
            request, 
            f"Updated environmental impact for {updated_count} rides"
        )
    calculate_environmental_impact.short_description = "Calculate environmental impact"

    def generate_metrics_report(self, request, queryset):
        """Generate a summary report for selected metrics"""
        total_distance = queryset.aggregate(Sum('distance_km'))['distance_km__sum'] or 0
        total_co2_saved = queryset.aggregate(Sum('co2_emissions_kg'))['co2_emissions_kg__sum'] or 0
        avg_comfort = queryset.aggregate(Avg('passenger_comfort_score'))['passenger_comfort_score__avg'] or 0
        
        self.message_user(
            request, 
            f"Report: {len(queryset)} rides, "
            f"Total Distance: {total_distance:.1f} km, "
            f"Total CO2: {total_co2_saved:.1f} kg, "
            f"Avg Comfort: {avg_comfort:.1f}/5.0"
        )
    generate_metrics_report.short_description = "Generate metrics report"


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'value', 'target', 'unit', 
        'performance_indicator', 'period_display', 'calculated_at'
    ]
    list_filter = [KPICategoryFilter, 'calculated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['calculated_at']
    fieldsets = [
        ('KPI Information', {
            'fields': ['name', 'description', 'category', 'unit']
        }),
        ('Values', {
            'fields': ['value', 'target']
        }),
        ('Period', {
            'fields': ['period_start', 'period_end']
        }),
        ('Metadata', {
            'fields': ['calculated_at'],
            'classes': ['collapse']
        })
    ]
    actions = ['update_kpi_values', 'export_kpi_data']

    def period_display(self, obj):
        return f"{obj.period_start.strftime('%Y-%m-%d')} to {obj.period_end.strftime('%Y-%m-%d')}"
    period_display.short_description = 'Period'

    def performance_indicator(self, obj):
        if obj.target:
            percentage = (obj.value / obj.target) * 100
            if percentage >= 100:
                color = 'green'
                icon = '✓'
            elif percentage >= 80:
                color = 'orange'
                icon = '→'
            else:
                color = 'red'
                icon = '✗'
            
            return format_html(
                '<span style="color: {};">{} {:.1f}%</span>',
                color, icon, percentage
            )
        return "No target set"
    performance_indicator.short_description = 'Performance'

    def update_kpi_values(self, request, queryset):
        """Recalculate KPI values based on current data"""
        from django.utils import timezone
        from datetime import timedelta
        
        updated_count = 0
        for kpi in queryset:
            # Example recalculation logic - replace with your actual calculations
            if kpi.category == 'environmental':
                # Calculate total CO2 savings
                total_co2 = RideMetrics.objects.filter(
                    created_at__range=[kpi.period_start, kpi.period_end]
                ).aggregate(Sum('co2_emissions_kg'))['co2_emissions_kg__sum'] or 0
                kpi.value = total_co2
                kpi.save()
                updated_count += 1
        
        self.message_user(
            request, 
            f"Updated values for {updated_count} KPIs"
        )
    update_kpi_values.short_description = "Recalculate KPI values"

    def export_kpi_data(self, request, queryset):
        """Export KPI data (placeholder for actual export functionality)"""
        self.message_user(
            request, 
            f"Prepared {queryset.count()} KPIs for export"
        )
    export_kpi_data.short_description = "Export KPI data"

    def save_model(self, request, obj, form, change):
        """Validate that period_end is after period_start"""
        if obj.period_end <= obj.period_start:
            raise ValidationError("Period end must be after period start")
        super().save_model(request, obj, form, change)


# ============ DASHBOARD CUSTOMIZATION ============
class AnalyticsAdminSite(admin.AdminSite):
    """Custom admin site for analytics models"""
    site_header = "Transport Analytics Administration"
    site_title = "Analytics Admin"
    index_title = "Analytics Dashboard"

    def index(self, request, extra_context=None):
        # Add analytics summary to the admin index
        extra_context = extra_context or {}
        
        # Basic statistics
        extra_context['total_ratings'] = Rating.objects.count()
        extra_context['avg_rating'] = Rating.objects.aggregate(
            avg=Avg('score')
        )['avg'] or 0
        extra_context['total_metrics'] = RideMetrics.objects.count()
        extra_context['active_kpis'] = KPI.objects.count()
        
        return super().index(request, extra_context)


# Register all models with the custom admin site
analytics_admin = AnalyticsAdminSite(name='analytics_admin')

analytics_admin.register(UserPreference, UserPreferenceAdmin)
analytics_admin.register(Rating, RatingAdmin)
analytics_admin.register(AnalyticsProfile, AnalyticsProfileAdmin)
analytics_admin.register(RideMetrics, RideMetricsAdmin)
analytics_admin.register(KPI, KPIAdmin)