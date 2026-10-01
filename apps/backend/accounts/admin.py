import logging

from django.contrib import admin, messages
from django.contrib.admin import AdminSite, SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html


from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import (Address,  Role, User,
                     UserProfile,  UserRole)

logger = logging.getLogger(__name__)

# Dummy SMS sending function (currently prints only)
def send_sms(to, message):
    print(f"Sending SMS to {to}: {message}")

# ================================
# CUSTOM FILTERS
# ================================

class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = 'user'
    extra = 0
    autocomplete_fields = ['role', 'created_by', 'verified_by', 'revoked_by']
    readonly_fields = ['created_at', 'verified_at', 'revoked_at']
    fields = [
        'role', 'is_active', 'created_by', 'created_at',
        'verified_by', 'verified_at', 'expires_at',
        'revoked_by', 'revoked_at', 'notes'
    ]

class AppRoleFilter(SimpleListFilter):
    title = "App Role"
    parameter_name = "app_role"

    def lookups(self, request, model_admin):
        apps = Role.objects.values_list('app_name', flat=True).distinct()
        return [(app, app.replace('_', ' ').title()) for app in apps if app]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_roles__role__app_name=self.value()).distinct()
        return queryset

class RoleNameFilter(SimpleListFilter):
    title = "Role Name"
    parameter_name = "role_name"

    def lookups(self, request, model_admin):
        roles = Role.objects.values_list('name', flat=True).distinct()
        return [(role, role.replace('_', ' ').title()) for role in roles if role]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_roles__role__name=self.value()).distinct()
        return queryset

class VerificationLevelFilter(SimpleListFilter):
    title = "Verification Level"
    parameter_name = "verification_level"

    def lookups(self, request, model_admin):
        return (
            ('0', 'Unverified'),
            ('1', 'Basic'),
            ('2', 'ID Verified'),
            ('3', 'Address Verified'),
            ('4', 'Payment Verified'),
            ('5', 'Premium Verified')
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(profile__verification_level=self.value())
        return queryset

# ================================
# MAIN ADMIN REGISTRATIONS
# ================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = (
        'email', 
        'phone_number_display', 
        'full_name',
        'is_staff', 
        'is_active',
        'verification_status',
        'roles_display'
    )
    list_filter = (
        'is_staff', 
        'is_active', 
        AppRoleFilter,
        RoleNameFilter,
        VerificationLevelFilter
    )
    search_fields = (
        'email', 
        'phone_number', 
        'first_name', 
        'last_name',
        'profile__id_number'
    )
    ordering = ('-date_joined',)
    readonly_fields = (
        'last_login', 
        'date_joined',
        'verification_badge'
    )
    inlines = [UserRoleInline]
    actions = ['send_sms_to_users', 'export_users']
    list_select_related = ['profile']

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {
            "fields": (
                "first_name", 
                "last_name", 
                "phone_number",
                
            )
        }),
        ("Permissions", {
            "fields": (
                "is_staff", 
                "is_active", 
                "is_superuser",
                "groups", 
                "user_permissions"
            )
        }),
        ("Important dates", {
            "fields": (
                "last_login", 
                "date_joined"
            )
        }),
        ("Verification", {
            "fields": (
                "verification_badge",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", 
                "phone_number", 
                "password1", 
                "password2", 
                "is_staff", 
                "is_active"
            ),
        }),
    )

    @admin.display(description="Phone")
    def phone_number_display(self, obj):
        return obj.phone_number or "-"

    @admin.display(description="Full Name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "-"

    @admin.display(description="Verification")
    def verification_status(self, obj):
        if not hasattr(obj, 'profile'):
            return "-"
        return obj.profile.get_verification_badge()

    @admin.display(description="Roles")
    def roles_display(self, obj):
        roles = obj.user_roles.filter(is_active=True).select_related('role')
        return ", ".join([f"{r.role.app_name}:{r.role.name}" for r in roles])

    @admin.display(description="Verification Badge")
    def verification_badge(self, obj):
        if not hasattr(obj, 'profile'):
            return "-"
        level = obj.profile.verification_level
        colors = {
            0: "gray",
            1: "blue",
            2: "green",
            3: "purple",
            4: "orange",
            5: "gold"
        }
        return format_html(
            '<span style="color: {}; font-weight: bold">{}</span>',
            colors.get(level, "black"),
            obj.profile.get_verification_badge()
        )

    @admin.action(description="Send SMS to selected users")
    def send_sms_to_users(self, request, queryset):
        success_count = 0
        for user in queryset:
            if user.phone_number:
                try:
                    message = f"Hi {user.first_name or 'there'}, message from admin"
                    send_sms(to=str(user.phone_number), message=message)
                    success_count += 1
                except Exception as e:
                    logger.error(f"SMS send failed for {user.email}: {str(e)}")
                    self.message_user(
                        request, 
                        f"Failed to send SMS to {user.email}", 
                        level=messages.ERROR
                    )
            else:
                self.message_user(
                    request, 
                    f"{user.email} has no phone number", 
                    level=messages.WARNING
                )

        self.message_user(
            request, 
            f"SMS sent to {success_count} user(s)", 
            level=messages.SUCCESS
        )

    @admin.action(description="Export selected users")
    def export_users(self, request, queryset):
        # Implement your export logic here
        self.message_user(request, "Export functionality not yet implemented", level=messages.INFO)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'phone_display',
        'verification_status_display',
        'verification_level_display',
        'age',
        'last_active',
        'is_online'
    )
    list_filter = (
        'verification_status',
        'gender',
        'preferred_notification_method',
        'is_online',
        'created_at'
    )
    search_fields = (
        'user__email',
        'user__phone_number',
        'id_number',
        'search_document'
    )
    readonly_fields = (
        'created_at',
        'updated_at',
        'rating',
        'verification_status_display',
        'verification_level_display',
        'last_active',
        'age',
    )
    raw_id_fields = ('user',)
    list_select_related = ['user']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            "fields": ("user", "profile_picture")
        }),
        ("Personal Info", {
            "fields": (
                "date_of_birth",
                "gender",
                "language_code"
            )
        }),
        ("Identification", {
            "fields": (
                "id_type",
                "id_number",
                "id_image"
            )
        }),
        ("Verification", {
            "fields": (
                "verification_status",
                "verification_status_display",
                "verification_level_display",
                "verification_date",
                "verified_by"
            )
        }),
        ("Activity", {
            "fields": (
                "rating",
                "last_active",
                "is_online"
            )
        }),
        ("Preferences", {
            "fields": ("preferred_notification_method",)
        }),
        ("Metadata", {
            "fields": (
                "created_at",
                "updated_at",
                "note"
            )
        }),
    )

    @admin.display(description="Phone")
    def phone_display(self, obj):
        return obj.user.phone_number if obj.user else "-"

    @admin.display(description="Verification Status")
    def verification_status_display(self, obj):
        colors = {
            'unverified': "gray",
            'basic': "blue", 
            'id_verified': "green",
            'address_verified': "purple",
            'payment_verified': "orange",
            'premium_verified': "gold"
        }
        return format_html(
            '<span style="color: {}; font-weight: bold">{}</span>',
            colors.get(obj.verification_status, "black"),
            obj.get_verification_badge()
        )

    @admin.display(description="Verification Level")
    def verification_level_display(self, obj):
        level = obj.verification_level
        colors = {
            0: "gray",
            1: "blue",
            2: "green", 
            3: "purple",
            4: "orange",
            5: "gold"
        }
        return format_html(
            '<span style="color: {}; font-weight: bold">Level {}</span>',
            colors.get(level, "black"),
            level
        )

    # Add custom filters for the properties if needed
    class VerificationStatusFilter(admin.SimpleListFilter):
        title = 'verification status (custom)'
        parameter_name = 'verification_status_custom'

        def lookups(self, request, model_admin):
            return [
                ('verified', 'Verified'),
                ('unverified', 'Unverified'),
            ]

        def queryset(self, request, queryset):
            if self.value() == 'verified':
                return queryset.exclude(verification_status='unverified')
            if self.value() == 'unverified':
                return queryset.filter(verification_status='unverified')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'app_name_display',
        'is_default',
        'requires_verification',
        'permissions_count'
    )
    list_filter = ('app_name', 'is_default', 'requires_verification')
    search_fields = ('name', 'app_name', 'description')
    filter_horizontal = ('permissions',)
    
    # Only include fields that actually exist in your model
    # readonly_fields = ()  # Remove this line if no readonly fields exist
    
    @admin.display(description="App")
    def app_name_display(self, obj):
        return obj.get_app_name_display()

    @admin.display(description="Permissions")
    def permissions_count(self, obj):
        return obj.permissions.count()
    

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'role',
        'is_active',
        'created_at',
        'verified_status',
        'expiry_status'
    )
    list_filter = (
        'is_active',
        'role__app_name',
        'role__name'
    )
    search_fields = (
        'user__email',
        'role__name',
        'role__app_name'
    )
    readonly_fields = (
        'created_at',
        'verified_at',
        'revoked_at'
    )
    raw_id_fields = ('user', 'role')
    list_select_related = ['user', 'role']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            "fields": ("user", "role", "is_active")
        }),
        ("Assignment", {
            "fields": ("created_by", "created_at", "notes")
        }),
        ("Verification", {
            "fields": (
                "verified_by",  # Changed from requires_verification
                "verified_at"
            )
        }),
        ("Status", {
            "fields": (
                "expires_at",
                "revoked_by",
                "revoked_at"
            )
        }),
    )

    @admin.display(description="Verified")
    def verified_status(self, obj):
        if obj.verified_at:
            return format_html(
                '<span style="color: green">✓ {}</span>',
                obj.verified_at.strftime("%Y-%m-%d")
            )
        return format_html('<span style="color: gray">✗</span>')

    @admin.display(description="Expires")
    def expiry_status(self, obj):
        if not obj.expires_at:
            return "-"
        
        if obj.expires_at < timezone.now():
            return format_html(
                '<span style="color: red">Expired {}</span>',
                obj.expires_at.strftime("%Y-%m-%d")
            )
        return obj.expires_at.strftime("%Y-%m-%d")



@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "address_type_display",
        "city_state_country",
        "is_default",
        "created_at",
    )
    list_filter = (
        "address_type",
        "is_default",
        "country",
    )
    search_fields = (
        "user__email",
        "street_address_1",
        "street_address_2",
        "city",
        "state",
        "postal_code",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("user",)
    list_select_related = ["user"]

    @admin.display(description="Type")
    def address_type_display(self, obj):
        return obj.get_address_type_display()

    @admin.display(description="Location")
    def city_state_country(self, obj):
        parts = [
            value
            for value in (
                obj.city,
                obj.state,
                obj.country.name if obj.country else None,
            )
            if value
        ]
        return ", ".join(parts) or "—"

# ================================
# CUSTOM ADMIN SITE
# ================================

class MyAdminSite(AdminSite):
    site_header = 'Accounts Administration'
    site_title = 'Accounts Admin Portal'
    index_title = 'Welcome to Accounts Admin'

    def get_app_list(self, request):
        """
        Customize the app list ordering and grouping
        """
        app_list = super().get_app_list(request)
        
        # Reorder the apps as desired
        ordered_apps = []
        app_ordering = [
            'accounts',
            'auth',
            # Add other apps here as needed
        ]
        
        for app_name in app_ordering:
            for app in app_list:
                if app['app_label'] == app_name:
                    ordered_apps.append(app)
                    break
        
        return ordered_apps

admin_site = MyAdminSite(name='myadmin')

# Register all models with the custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(Role, RoleAdmin)
admin_site.register(UserRole, UserRoleAdmin)
admin_site.register(Address, AddressAdmin)
