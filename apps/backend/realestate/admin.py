# admin.py - FIXED VERSION

from django.contrib import admin
from django.contrib.admin.widgets import AdminFileWidget
from django.contrib.gis.admin import GISModelAdmin 
from django.db import models
from django.forms import ClearableFileInput, Textarea
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.indexes import GinIndex, BTreeIndex
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from django.urls import reverse
from django.utils.safestring import mark_safe


from .models import (
    Listing, ListingFile, ListingImage, 
    ListingType, ListingCategory, Agent,
    CommissionPlan, PropertyRating, Transaction,
    Client, AgentProfile, LocationPreference,
    PropertyProximity, Offer, PropertyUpdateLog,
    PropertySubscription, AgentRating
)


# Add this admin registration

# =====================
# ADMIN ACTIONS
# =====================
@admin.action(description=_("Mark selected listings as published"))
def set_online(modeladmin, request, queryset):
    queryset.update(is_published=True)
    modeladmin.message_user(request, _("Successfully published selected listings"))


@admin.action(description=_("Mark selected listings as unpublished"))
def set_offline(modeladmin, request, queryset):
    queryset.update(is_published=False)
    modeladmin.message_user(request, _("Successfully unpublished selected listings"))


@admin.action(description=_("Verify selected agents"))
def verify_agents(modeladmin, request, queryset):
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(request, f'{updated} agents verified successfully')


@admin.action(description=_("Unverify selected agents"))
def unverify_agents(modeladmin, request, queryset):
    updated = queryset.update(is_verified=False)
    modeladmin.message_user(request, f'{updated} agents unverified')


# =====================
# CUSTOM WIDGETS
# =====================
class AdminImagePreviewWidget(AdminFileWidget):
    def render(self, name, value, attrs=None, renderer=None):
        output = []
        if value and getattr(value, "url", None):
            image_url = value.url
            file_name = str(value)
            output.append(
                f'<a href="{image_url}" target="_blank">'
                f'<img src="{image_url}" alt="{file_name}" style="max-height: 150px; max-width: 150px; object-fit: contain;"/>'
                f'</a><br/>'
            )
        output.append(super().render(name, value, attrs, renderer))
        return mark_safe(''.join(output))


# =====================
# INLINE ADMINS
# =====================
class ListingImageInline(admin.StackedInline):
    model = ListingImage
    formfield_overrides = {
        models.ImageField: {"widget": AdminImagePreviewWidget},
        models.TextField: {"widget": Textarea(attrs={"rows": 3, "cols": 40})},
    }
    extra = 1
    classes = ['collapse']
    verbose_name = _("Property Image")
    verbose_name_plural = _("Property Images")
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('listing')


class ListingFileInline(admin.StackedInline):
    model = ListingFile
    extra = 1
    classes = ['collapse']
    verbose_name = _("Property Document")
    verbose_name_plural = _("Property Documents")
    fields = ('file', 'name', 'short_description', 'for_customer')
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 3, "cols": 40})},
    }



@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "company_name",
        "years_experience",
        "has_agent_record",
    )

    list_filter = (
        "company_name",
        "years_experience",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "company_name",
        "specialization",
        "languages",
    )

    autocomplete_fields = (
        "user",
    )

    readonly_fields = (
        "has_agent_record_display",
        "company_logo_tag",
    )

    fieldsets = (
        (
            "User",
            {
                "fields": (
                    "user",
                )
            },
        ),
        (
            "Profile Information",
            {
                "fields": (
                    "company_name",
                    "company_logo",
                    "company_logo_tag",
                    "bio",
                    "years_experience",
                )
            },
        ),
        (
            "Skills & Specialization",
            {
                "fields": (
                    "specialization",
                    "languages",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Agent Connection",
            {
                "fields": (
                    "has_agent_record_display",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="User",
        ordering="user__email",
    )
    def user_display(self, obj):
        user = obj.user
        return (
            user.get_full_name()
            or user.email
            or str(getattr(user, 'phone_number', ''))
        )

    @admin.display(
        description="Company Logo",
        boolean=False,
    )
    def company_logo_tag(self, obj):
        """Display company logo thumbnail."""
        if obj.company_logo:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />',
                obj.company_logo.url
            )
        return "No logo"

    @admin.display(
        description="Has Agent Record",
        boolean=True,
    )
    def has_agent_record(self, obj):
        """Check if the agent profile has a related Agent record."""
        return hasattr(obj, 'agent') and obj.agent is not None

    @admin.display(
        description="Agent Status",
    )
    def has_agent_record_display(self, obj):
        """Display agent connection status."""
        agent = getattr(obj, 'agent', None)
        if agent:
            return format_html(
                '<span style="color: green;">✓ Agent Record Connected</span><br>'
                '<small>Verified: {}<br>'
                'Active: {}<br>'
                'Rating: {:.1f}/5.0</small>',
                "Yes" if agent.is_verified else "No",
                "Yes" if agent.is_active else "No",
                agent.agent_rating or 0,
            )
        return format_html(
            '<span style="color: orange;">⚠ No Agent Record</span><br>'
            '<small>Create an Agent record for this profile</small>'
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("agent")
        )


@admin.register(Agent)
class AgentAdmin(GISModelAdmin):
    list_display = (
        "agent_display",
        "license_number",
        "is_verified",
        "is_active",
        "agent_rating",
        "total_listings",
        "total_sales_display",
        "created_at_display",
    )

    list_filter = (
        "is_verified",
        "is_active",
        "created",
        
    )

    search_fields = (
        "agent_profile__user__email",
        "agent_profile__user__first_name",
        "agent_profile__user__last_name",
        "license_number",
    )

    autocomplete_fields = [
        "agent_profile",
    ]

    readonly_fields = (
        "created",
        "location_info_display",
        "agent_profile_display",
        "performance_metrics",
        "license_image_tag",
    )

    fieldsets = (
        (
            "Profile",
            {
                "fields": (
                    "agent_profile",
                    "agent_profile_display",
                )
            },
        ),
        (
            "Professional Information",
            {
                "fields": (
                    "license_number",
                    "license_image",
                    "license_image_tag",
                )
            },
        ),
        (
            "Verification & Status",
            {
                "fields": (
                    "is_verified",
                    "is_active",
                )
            },
        ),
        (
            "Performance Metrics",
            {
                "fields": (
                    "performance_metrics",
                )
            },
        ),
        (
            "Cached Metrics",
            {
                "fields": (
                    "agent_rating",
                    "total_listings",
                    "total_sales",
                    "total_reviews",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Location Information",
            {
                "fields": (
                    "location_point",
                    "location_info_display",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created",
                    
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "verify_agents",
        "unverify_agents",
        "activate_agents",
        "deactivate_agents",
        "update_metrics",
    ]

    @admin.display(
        description="Agent",
        ordering="agent_profile__user__email",
    )
    def agent_display(self, obj):
        """Display agent name with email."""
        if not obj.agent_profile:
            return "No profile"

        user = obj.agent_profile.user
        name = user.get_full_name().strip() or user.email or str(user)

        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            name,
            user.email or "",
        )

    @admin.display(
        description="Created",
        ordering="created",
    )
    def created_at_display(self, obj):
        """Display created date."""
        return obj.created.strftime("%Y-%m-%d")

    @admin.display(
        description="Total Sales",
        ordering="total_sales",
    )
    def total_sales_display(self, obj):
        """Display total sales with currency."""
        if obj.total_sales:
            return f"₦{obj.total_sales:,.2f}"
        return "₦0.00"

    @admin.display(
        description="License Image",
        boolean=False,
    )
    def license_image_tag(self, obj):
        """Display license image thumbnail."""
        if obj.license_image:
            return format_html(
                '<img src="{}" width="150" style="border-radius: 5px;" />',
                obj.license_image.url
            )
        return "No license image"

    @admin.display(
        description="Profile",
    )
    def agent_profile_display(self, obj):
        """Display agent profile information."""
        if not obj.agent_profile:
            return "No profile"

        profile = obj.agent_profile
        user = profile.user

        return format_html(
            """
            <div style="padding: 5px;">
                <strong>{}</strong><br>
                Company: {}<br>
                Experience: {} years
            </div>
            """,
            user.get_full_name() or user.email,
            profile.company_name or "Not set",
            profile.years_experience or 0,
        )

    @admin.display(
        description="Performance",
    )
    def performance_metrics(self, obj):
        """Display performance metrics in a formatted way."""
        return format_html(
            """
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                <strong>Rating:</strong> {:.1f}/5.0 ({})<br>
                <strong>Listings:</strong> {}<br>
                <strong>Sales:</strong> ₦{:,.2f}<br>
                <strong>Reviews:</strong> {}
            </div>
            """,
            obj.agent_rating or 0,
            obj.total_reviews or 0,
            obj.total_listings or 0,
            obj.total_sales or 0,
            obj.total_reviews or 0,
        )

    @admin.display(
        description="Location",
    )
    def location_info_display(self, obj):
        """Display detailed location information."""
        if not obj.location_point:
            return "No location data available"

        return format_html(
            """
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                <strong>Latitude:</strong> {}<br>
                <strong>Longitude:</strong> {}<br>
                <strong>SRID:</strong> 4326
            </div>
            """,
            obj.location_point.y if obj.location_point else "N/A",
            obj.location_point.x if obj.location_point else "N/A",
        )

    def get_queryset(self, request):
        """Optimize queryset with related account/profile data."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "agent_profile__user",
            )
        )

    # Admin actions
    def verify_agents(self, request, queryset):
        """Verify selected agents."""
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} agent(s) verified.")
    verify_agents.short_description = "Verify selected agents"

    def unverify_agents(self, request, queryset):
        """Unverify selected agents."""
        count = queryset.update(is_verified=False)
        self.message_user(request, f"{count} agent(s) unverified.")
    unverify_agents.short_description = "Unverify selected agents"

    def activate_agents(self, request, queryset):
        """Activate selected agents."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} agent(s) activated.")
    activate_agents.short_description = "Activate selected agents"

    def deactivate_agents(self, request, queryset):
        """Deactivate selected agents."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} agent(s) deactivated.")
    deactivate_agents.short_description = "Deactivate selected agents"

    def update_metrics(self, request, queryset):
        """Update metrics for selected agents."""
        for agent in queryset:
            agent.update_metrics()
        self.message_user(request, f"Metrics updated for {queryset.count()} agent(s).")
    update_metrics.short_description = "Update metrics for selected agents"


@admin.register(AgentRating)
class AgentRatingAdmin(admin.ModelAdmin):
    list_display = (
        "agent_display",
        "user_display",
        "rating",
        "review_preview",
        "created_at_display",
    )

    list_filter = (
        "rating",
        "created_at",
    )

    search_fields = (
        "agent__agent_profile__user__email",
        "agent__agent_profile__user__first_name",
        "agent__agent_profile__user__last_name",
        "user__email",
        "user__first_name",
        "user__last_name",
        "review",
    )

    autocomplete_fields = [
        "agent",
        "user",
    ]

    readonly_fields = (
        "created_at",
        "agent_display",
        "user_display",
    )

    fieldsets = (
        (
            "Rating Information",
            {
                "fields": (
                    "agent",
                    "agent_display",
                    "user",
                    "user_display",
                    "rating",
                    "review",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Agent",
        ordering="agent__agent_profile__user__email",
    )
    def agent_display(self, obj):
        """Display agent name."""
        if obj.agent and obj.agent.agent_profile:
            user = obj.agent.agent_profile.user
            name = user.get_full_name().strip() or user.email
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                user.email,
            )
        return "Unknown Agent"

    @admin.display(
        description="Reviewer",
        ordering="user__email",
    )
    def user_display(self, obj):
        """Display reviewer name."""
        user = obj.user
        name = user.get_full_name().strip() or user.email
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            name,
            user.email,
        )

    @admin.display(
        description="Created",
        ordering="created_at",
    )
    def created_at_display(self, obj):
        """Display created date."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    @admin.display(
        description="Review Preview",
    )
    def review_preview(self, obj):
        """Display a preview of the review."""
        if obj.review:
            return obj.review[:100] + "..." if len(obj.review) > 100 else obj.review
        return "No review"

    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "agent__agent_profile__user",
                "user",
            )
        ) 
  
        
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "search_radius_km",
        "price_range_min",
        "price_range_max",
        "notification_frequency",
        "created",
    )

    list_filter = (
        "notification_frequency",
        "created",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__phone_number",
    )

    readonly_fields = (
        "created",
        "updated",
    )

    autocomplete_fields = [
        "user",
    ]

    fieldsets = (
        (
            "Client Information",
            {
                "fields": (
                    "user",
                )
            },
        ),
        (
            "Search Preferences",
            {
                "fields": (
                    "search_radius_km",
                    "price_range_min",
                    "price_range_max",
                    "preferred_property_types",
                )
            },
        ),
        (
            "Notification Settings",
            {
                "fields": (
                    "notification_frequency",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created",
                    "updated",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
        )


# =====================
# MODEL ADMINS
# =====================
@admin.register(CommissionPlan)
class CommissionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'base_percentage', 'is_active']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name']


@admin.register(PropertyRating)
class PropertyRatingAdmin(admin.ModelAdmin):
    list_display = ['property', 'user', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['property__title', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ("listing_link", "get_image_preview", "short_description", "created")
    list_filter = ("listing__property_status", "listing__property_for")
    search_fields = ("listing__title", "short_description")
    readonly_fields = ("get_image_preview", "created", "updated")
    list_select_related = ('listing',)
    autocomplete_fields = ['listing']
    date_hierarchy = 'created'
    actions = [set_online, set_offline]

    def get_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; object-fit: contain;"/>',
                obj.image.url
            )
        return "-"
    get_image_preview.short_description = _("Preview")

    def listing_link(self, obj):
        url = reverse('admin:realestate_listing_change', args=[obj.listing.id])
        return mark_safe(f'<a href="{url}">{obj.listing.title}</a>')
    listing_link.short_description = _("Listing")
    listing_link.admin_order_field = "listing__title"

    fieldsets = (
        (None, {
            "fields": ("listing", "image", "short_description")
        }),
        (_("Preview"), {
            "fields": ("get_image_preview",)
        }),
        (_("Metadata"), {
            "fields": ("created", "updated"),
            "classes": ("collapse",)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('listing')


@admin.register(Listing)
class ListingAdmin(GISModelAdmin):
    list_display = (
        "title",
        "agent_link",
        "owner",
        "address_display",
        "listing_type",
        "property_for",
        "price_display",
        "property_status",
        "is_published",
        "created_short",
    )

    list_filter = (
        "listing_type",
        "property_for",
        "property_status",
        "is_published",
        "created",
    )

    search_fields = (
        "title",
        "description",
        "property_location",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
        "reviewer__email",
        "reviewer__first_name",
        "reviewer__last_name",
    )

    readonly_fields = (
        "created",
        "updated",
        "coordinates",
        "price_display",
        "nigerian_location_display",
        "num_images",
        "num_files",
        "display_price_field",
        "land_size_display_field",
        "plot_availability_display",
    )

    inlines = [
        ListingImageInline,
        ListingFileInline,
    ]

    autocomplete_fields = (
        "agent",
        "reviewer",
        "owner",
        "listing_type",
        "property_category",
    )

    date_hierarchy = "created"

    actions = [
        set_online,
        set_offline,
    ]

    save_on_top = True
    save_as = True

    list_per_page = 25
    list_max_show_all = 1000

    list_select_related = (
        "agent",
        "owner",
        "reviewer",
        "listing_type",
        "property_category",
    )

    # ------------------------------------------------------------------
    # Queryset
    # ------------------------------------------------------------------

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "agent",
                "owner",
                "reviewer",
                "listing_type",
                "property_category",
            )
            .prefetch_related(
                "images",
                "files",
            )
        )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @admin.display(
        description=_("Price"),
        ordering="price",
    )
    def price_display(self, obj):
        return (
            obj.display_price
            if hasattr(obj, "display_price")
            else (
                f"₦{obj.price:,.2f}"
                if obj.price
                else "-"
            )
        )

    @admin.display(
        description=_("Formatted Price"),
    )
    def display_price_field(self, obj):
        return (
            obj.display_price
            if hasattr(obj, "display_price")
            else (
                f"₦{obj.price:,.2f}"
                if obj.price
                else "Not set"
            )
        )

    @admin.display(
        description=_("Location"),
    )
    def address_display(self, obj):
        return (
            obj.property_location
            or obj.nigerian_location
            or "-"
        )

    @admin.display(
        description=_("Agent"),
    )
    def agent_link(self, obj):
        if not obj.agent:
            return "-"

        url = reverse(
            "admin:realestate_agent_change",
            args=[obj.agent.id],
        )

        agent_name = (
            obj.agent.display_name
            if hasattr(obj.agent, "display_name")
            else str(obj.agent)
        )

        return mark_safe(
            f'<a href="{url}">{agent_name}</a>'
        )

    @admin.display(
        description=_("Created"),
        ordering="created",
    )
    def created_short(self, obj):
        return obj.created.date()

    @admin.display(
        description=_("Images Count"),
    )
    def num_images(self, obj):
        return obj.images.count()

    @admin.display(
        description=_("Files Count"),
    )
    def num_files(self, obj):
        return obj.files.count()

    @admin.display(
        description=_("Land Size"),
    )
    def land_size_display_field(self, obj):
        if hasattr(obj, "land_size_display"):
            return obj.land_size_display

        if obj.land_size:
            return f"{obj.land_size} {obj.land_unit}"

        return "-"

    @admin.display(
        description=_("Plot Availability"),
    )
    def plot_availability_display(self, obj):
        return (
            obj.plot_availability
            if hasattr(obj, "plot_availability")
            else "-"
        )

    @admin.display(
        description=_("Nigerian Location"),
    )
    def nigerian_location_display(self, obj):
        return (
            obj.nigerian_location
            if hasattr(obj, "nigerian_location")
            else "-"
        )

    # ------------------------------------------------------------------
    # Fieldsets
    # ------------------------------------------------------------------

    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "title",
                    "description",
                    "property_location",
                    "listing_type",
                    "property_category",
                )
            },
        ),
        (
            _("Nigerian Location"),
            {
                "fields": (
                    "state",
                    "lga",
                    "estate_name",
                    "nigerian_location_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Property Details"),
            {
                "fields": (
                    "property_area",
                    "property_for",
                    "price",
                    "price_metric",
                    "display_price_field",
                    "bedrooms",
                    "bathrooms",
                    "garage",
                    "square_feet",
                    "lot_size",
                    "ceiling_height",
                    "year_built",
                )
            },
        ),
        (
            _("Land Details"),
            {
                "fields": (
                    "land_size",
                    "land_unit",
                    "land_size_display_field",
                    "total_plots",
                    "plots_available",
                    "plot_availability_display",
                    "price_per_plot",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Nigerian Property Features"),
            {
                "fields": (
                    "has_c_of_o",
                    "has_governors_consent",
                    "is_gated_estate",
                    "has_road_access",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Status and Publication"),
            {
                "fields": (
                    "property_status",
                    "is_published",
                    "free_from",
                    "agent",
                    "owner",
                    "reviewer",
                )
            },
        ),
        (
            _("Media"),
            {
                "fields": (
                    "image",
                    "num_images",
                    "num_files",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "created",
                    "updated",
                    "coordinates",
                ),
                "classes": ("collapse",),
            },
        ),
    )



@admin.register(ListingType)
class ListingTypeAdmin(admin.ModelAdmin):
    list_display = ("property_type", "created_short", "updated_short", "listing_count")
    search_fields = ("property_type",)
    ordering = ("property_type",)
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _listing_count=models.Count('listing')
        )
    
    def listing_count(self, obj):
        return obj._listing_count
    listing_count.short_description = _("Listings")
    listing_count.admin_order_field = '_listing_count'
    
    def created_short(self, obj):
        return obj.created.date()
    created_short.short_description = _("Created")
    
    def updated_short(self, obj):
        return obj.updated.date()
    updated_short.short_description = _("Updated")


@admin.register(ListingCategory)
class ListingCategoryAdmin(DraggableMPTTAdmin):
    list_display = (
        'tree_actions',
        'indented_title',
        'slug',
        'listing_count',
        'updated_short',
    )
    list_display_links = ('indented_title', 'slug')
    search_fields = ('name', 'slug', 'description_plaintext')
    list_filter = ('updated_at',)
    ordering = ('tree_id', 'lft')
    prepopulated_fields = {"slug": ("name",)}
    mptt_level_indent = 20
    expand_tree_by_default = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('parent').annotate(
            _listing_count=models.Count('products')
        )
    
    def listing_count(self, obj):
        return obj._listing_count
    listing_count.short_description = _("Listings")
    listing_count.admin_order_field = '_listing_count'
    
    def updated_short(self, obj):
        return obj.updated_at.date()
    updated_short.short_description = _("Updated")
    
    def indented_title(self, obj):
        return super().indented_title(obj)
    indented_title.short_description = _("Category Name")


@admin.register(ListingFile)
class ListingFileAdmin(admin.ModelAdmin):
    list_display = (
        "listing_link",
        "name",
        "short_description",
        "file_type_display",
        "for_customer",
        "created_short",
    )
    search_fields = [
        "listing__title",
        "name",
        "short_description",
    ]
    list_filter = ("for_customer", "created")
    autocomplete_fields = ["listing"]
    readonly_fields = ("updated", "created", "file_type_display", "file_size_display")
    date_hierarchy = 'created'
    list_select_related = ('listing',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('listing')
    
    def listing_link(self, obj):
        url = reverse('admin:realestate_listing_change', args=[obj.listing.id])
        return mark_safe(f'<a href="{url}">{obj.listing.title}</a>')
    listing_link.short_description = _("Listing")
    listing_link.admin_order_field = "listing__title"
    
    def created_short(self, obj):
        return obj.created.date()
    created_short.short_description = _("Created")
    
    def file_type_display(self, obj):
        if obj.file:
            return obj.file.name.split('.')[-1].upper()
        return "-"
    file_type_display.short_description = _("Type")
    
    def file_size_display(self, obj):
        if obj.file:
            return f"{obj.file.size / 1024:.1f} KB"
        return "-"
    file_size_display.short_description = _("Size")
    
    fieldsets = (
        (None, {
            "fields": ("listing", "file", "name", "short_description", "for_customer")
        }),
        (_("Metadata"), {
            "fields": ("file_type_display", "file_size_display", "created", "updated"),
            "classes": ("collapse",)
        }),
    )


@admin.register(LocationPreference)
class LocationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user_display",
        "radius_km",
        "coordinates_display",
    )

    list_filter = (
        "radius_km",
    )

    search_fields = (
        "name",
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__phone_number",
    )

    autocomplete_fields = (
        "user",
    )

    readonly_fields = (
        "latitude_display",
        "longitude_display",
    )

    fieldsets = (
        (
            "Preference Information",
            {
                "fields": (
                    "name",
                    "user",
                    "radius_km",
                ),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "location_point",
                    "latitude_display",
                    "longitude_display",
                ),
            },
        ),
    )

    def user_display(self, obj):
        """Display the account associated with this preference."""
        user = obj.user

        if not user:
            return "No user"

        name = user.get_full_name().strip()

        if name:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                user.email or "",
            )

        return user.email or str(user)

    user_display.short_description = "User"
    user_display.admin_order_field = "user__email"

    def coordinates_display(self, obj):
        """Display geographic coordinates."""
        if not obj.location_point:
            return "-"

        return f"{obj.location_point.y}, {obj.location_point.x}"

    coordinates_display.short_description = "Coordinates"

    def latitude_display(self, obj):
        """Display latitude."""
        return obj.latitude if obj.latitude is not None else "-"

    latitude_display.short_description = "Latitude"

    def longitude_display(self, obj):
        """Display longitude."""
        return obj.longitude if obj.longitude is not None else "-"

    longitude_display.short_description = "Longitude"

    def get_queryset(self, request):
        """Optimize account lookup."""
        return (
            super()
            .get_queryset(request)
            .select_related("user")
        )


@admin.register(PropertyProximity)
class PropertyProximityAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "buyer_display",
        "distance_display",
        "is_in_preferred_location",
        "calculated_at",
    )

    list_filter = (
        "is_in_preferred_location",
        "calculated_at",
    )

    search_fields = (
        "property__title",
        "property__slug",
        "buyer__user__email",
        "buyer__user__first_name",
        "buyer__user__last_name",
        "buyer__user__phone_number",
    )

    autocomplete_fields = (
        "property",
        "buyer",
    )

    readonly_fields = (
        "distance_display",
        "calculated_at",
        "coordinates_display",
    )

    fieldsets = (
        (
            "Property & Buyer",
            {
                "fields": (
                    "property",
                    "buyer",
                ),
            },
        ),
        (
            "Proximity",
            {
                "fields": (
                    "distance_km",
                    "distance_display",
                    "is_in_preferred_location",
                ),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "coordinates_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Calculation",
            {
                "fields": (
                    "calculated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def buyer_display(self, obj):
        """Display the real-estate client account."""
        if not obj.buyer:
            return "No client"

        user = obj.buyer.user

        if not user:
            return str(obj.buyer)

        name = user.get_full_name().strip()

        if name:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                user.email or "",
            )

        return user.email or str(user)

    buyer_display.short_description = "Buyer"
    buyer_display.admin_order_field = "buyer__user__email"

    def distance_display(self, obj):
        """Display proximity distance."""
        if obj.distance_km is None:
            return "-"

        return f"{obj.distance_km:,.2f} km"

    distance_display.short_description = "Distance"
    distance_display.admin_order_field = "distance_km"

    def coordinates_display(self, obj):
        """Display listing coordinates."""
        point = getattr(obj.property, "location_point", None)

        if not point:
            return "No location coordinates"

        return f"Latitude: {point.y}, Longitude: {point.x}"

    coordinates_display.short_description = "Property Coordinates"

    def get_queryset(self, request):
        """Optimize property and client/account lookups."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "property",
                "buyer",
                "buyer__user",
            )
        )


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "buyer_display",
        "offer_price_display",
        "status",
        "expiration_display",
        "created_at_display",
    )

    list_filter = (
        "status",
        "created_at",
        "expiration_date",
    )

    search_fields = (
        "property__title",
        "buyer__user__email",
        "buyer__user__first_name",
        "buyer__user__last_name",
        "buyer__user__phone_number",
    )

    autocomplete_fields = (
        "property",
        "buyer",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "is_expired_display",
    )

    date_hierarchy = "created_at"

    ordering = (
        "-created_at",
    )

    list_per_page = 25

    save_on_top = True

    fieldsets = (
        (
            _("Offer Information"),
            {
                "fields": (
                    "property",
                    "buyer",
                    "offer_price",
                    "status",
                    "message",
                )
            },
        ),
        (
            _("Expiration"),
            {
                "fields": (
                    "expiration_date",
                    "is_expired_display",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "property",
                "buyer__user",
            )
        )

    @admin.display(
        description=_("Buyer"),
        ordering="buyer__user__email",
    )
    def buyer_display(self, obj):
        """
        Display the real-estate Client's underlying User.
        """
        if not obj.buyer:
            return "-"

        user = obj.buyer.user

        if not user:
            return "-"

        name = user.get_full_name().strip()

        if name:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                user.email or "-",
            )

        return user.email or "-"

    @admin.display(
        description=_("Offer Price"),
        ordering="offer_price",
    )
    def offer_price_display(self, obj):
        if obj.offer_price is None:
            return "-"

        return f"₦{obj.offer_price:,.2f}"

    @admin.display(
        description=_("Expiration"),
        ordering="expiration_date",
    )
    def expiration_display(self, obj):
        if not obj.expiration_date:
            return "-"

        return obj.expiration_date.strftime("%Y-%m-%d %H:%M")

    @admin.display(
        description=_("Created"),
        ordering="created_at",
    )
    def created_at_display(self, obj):
        if not obj.created_at:
            return "-"

        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    @admin.display(
        description=_("Expired?"),
        boolean=True,
    )
    def is_expired_display(self, obj):
        return obj.is_expired()



@admin.register(PropertyUpdateLog)
class PropertyUpdateLogAdmin(admin.ModelAdmin):
    """
    Django admin configuration for real-estate property update logs.

    PropertyUpdateLog is an audit record. It is therefore intentionally
    read-only from the admin interface.
    """

    list_display = (
        "property_display",
        "updated_by_display",
        "changed_fields_display",
        "timestamp",
    )

    list_filter = (
        "timestamp",
    )

    search_fields = (
        "property__title",
        "property__property_location",
        "updated_by__email",
        "updated_by__first_name",
        "updated_by__last_name",
        "updated_by__phone_number",
    )

    readonly_fields = (
        "property",
        "updated_by",
        "changed_fields",
        "changed_fields_display",
        "change_summary_display",
        "timestamp",
    )

    autocomplete_fields = (
        "property",
        "updated_by",
    )

    date_hierarchy = "timestamp"

    ordering = (
        "-timestamp",
    )

    list_per_page = 50

    fieldsets = (
        (
            _("Update Information"),
            {
                "fields": (
                    "property",
                    "updated_by",
                    "timestamp",
                ),
            },
        ),
        (
            _("Changed Fields"),
            {
                "fields": (
                    "changed_fields",
                    "changed_fields_display",
                    "change_summary_display",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "property",
                "updated_by",
            )
        )

    @admin.display(
        description=_("Property"),
        ordering="property__title",
    )
    def property_display(self, obj):
        if not obj.property:
            return "-"

        return (
            obj.property.title
            or f"Listing #{obj.property.pk}"
        )

    @admin.display(
        description=_("Updated By"),
        ordering="updated_by__email",
    )
    def updated_by_display(self, obj):
        if not obj.updated_by:
            return "-"

        name = obj.updated_by.get_full_name()

        if name:
            return f"{name} ({obj.updated_by.email})"

        return obj.updated_by.email or str(obj.updated_by)

    @admin.display(
        description=_("Changed Fields"),
    )
    def changed_fields_display(self, obj):
        fields = obj.get_changed_fields()

        if not fields:
            return "-"

        return ", ".join(fields)

    @admin.display(
        description=_("Change Summary"),
    )
    def change_summary_display(self, obj):
        return obj.get_change_summary()



@admin.register(PropertySubscription)
class PropertySubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "property_type_display",
        "location_display",
        "radius_display",
        "notification_frequency",
        "is_active",
        "last_notified",
        "created_at",
    )

    list_filter = (
        "is_active",
        "notification_frequency",
        "property_type",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__phone_number",
        "property_type",
    )

    autocomplete_fields = (
        "user",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_notified",
        "location_info_display",
    )

    fieldsets = (
        (
            "Subscription",
            {
                "fields": (
                    "user",
                    "property_type",
                    "is_active",
                    "notification_frequency",
                )
            },
        ),
        (
            "Location Preferences",
            {
                "fields": (
                    "location_point",
                    "radius_km",
                    "location_info_display",
                )
            },
        ),
        (
            "Notification Information",
            {
                "fields": (
                    "last_notified",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    ordering = (
        "-created_at",
    )

    list_select_related = (
        "user",
    )

    @admin.display(
        description="User",
        ordering="user__email",
    )
    def user_display(self, obj):
        """Display the subscription owner."""
        user = obj.user

        if not user:
            return "No User"

        name = user.get_full_name().strip()

        if name:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                user.email or "No email",
            )

        return user.email or str(user)

    @admin.display(
        description="Property Type",
        ordering="property_type",
    )
    def property_type_display(self, obj):
        """Display the subscribed property type."""
        return obj.property_type or "All Properties"

    @admin.display(
        description="Location",
    )
    def location_display(self, obj):
        """Display the configured subscription location."""
        if not obj.location_point:
            return "Any Location"

        latitude = obj.location_point.y
        longitude = obj.location_point.x

        return f"{latitude:.6f}, {longitude:.6f}"

    @admin.display(
        description="Radius",
        ordering="radius_km",
    )
    def radius_display(self, obj):
        """Display the subscription search radius."""
        return f"{obj.radius_km} km"

    @admin.display(
        description="Location Details",
    )
    def location_info_display(self, obj):
        """Display detailed geographic subscription information."""
        if not obj.location_point:
            return "No location configured"

        latitude = obj.location_point.y
        longitude = obj.location_point.x

        return format_html(
            """
            <div style="background:#f8f9fa;padding:12px;border-radius:6px;">
                <strong>Latitude:</strong> {}<br>
                <strong>Longitude:</strong> {}<br>
                <strong>Radius:</strong> {} km<br>
                <strong>Property Type:</strong> {}
            </div>
            """,
            f"{latitude:.6f}",
            f"{longitude:.6f}",
            obj.radius_km,
            obj.property_type or "All Properties",
        )

    def get_queryset(self, request):
        """
        Optimize the admin queryset by loading the related user.
        """
        return (
            super()
            .get_queryset(request)
            .select_related("user")
        )



@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_display",
        "property_display",
        "buyer_display",
        "seller_display",
        "status",
        "offer_price",
        "agreed_price",
        "target_close_date",
        "actual_close_date",
        "created_at",
    )

    list_filter = (
        "status",
        "target_close_date",
        "actual_close_date",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "property__title",
        "buyer__user__email",
        "buyer__user__first_name",
        "buyer__user__last_name",
        "buyer__user__phone_number",
        "seller__email",
        "seller__first_name",
        "seller__last_name",
        "seller__phone_number",
        "escrow_number",
        "notes",
    )

    autocomplete_fields = (
        "property",
        "buyer",
        "seller",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "transaction_status_display",
    )

    fieldsets = (
        (
            "Transaction Parties",
            {
                "fields": (
                    "property",
                    "buyer",
                    "seller",
                )
            },
        ),
        (
            "Transaction Status",
            {
                "fields": (
                    "status",
                    "transaction_status_display",
                )
            },
        ),
        (
            "Financial Information",
            {
                "fields": (
                    "offer_price",
                    "agreed_price",
                    "escrow_number",
                )
            },
        ),
        (
            "Closing Information",
            {
                "fields": (
                    "target_close_date",
                    "actual_close_date",
                )
            },
        ),
        (
            "Notes",
            {
                "fields": (
                    "notes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    ordering = (
        "-created_at",
    )

    list_select_related = (
        "property",
        "buyer__user",
        "seller",
    )

    @admin.display(
        description="Transaction",
        ordering="id",
    )
    def transaction_display(self, obj):
        """Display the transaction identifier."""
        return f"#{obj.pk}"

    @admin.display(
        description="Property",
        ordering="property__title",
    )
    def property_display(self, obj):
        """Display the associated property."""
        if not obj.property:
            return "No Property"

        return obj.property.title or f"Property #{obj.property.pk}"

    @admin.display(
        description="Buyer",
        ordering="buyer__user__email",
    )
    def buyer_display(self, obj):
        """
        Display the real-estate Client buyer.

        Client owns the real-estate relationship and points
        directly to the central accounts.User.
        """
        if not obj.buyer:
            return "No Buyer"

        user = obj.buyer.user

        if not user:
            return "No User"

        name = user.get_full_name().strip()

        if name:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                user.email or "No email",
            )

        return user.email or str(user)

    @admin.display(
        description="Seller",
        ordering="seller__email",
    )
    def seller_display(self, obj):
        """
        Display the central accounts.User who is the seller.
        """
        if not obj.seller:
            return "No Seller"

        name = obj.seller.get_full_name().strip()

        if name:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                name,
                obj.seller.email or "No email",
            )

        return obj.seller.email or str(obj.seller)

    @admin.display(
        description="Status",
    )
    def transaction_status_display(self, obj):
        """
        Display a human-readable transaction status.
        """
        return obj.get_status_display()

    def get_queryset(self, request):
        """
        Optimize the transaction admin queryset.
        """
        return (
            super()
            .get_queryset(request)
            .select_related(
                "property",
                "buyer__user",
                "seller",
            )
        )
