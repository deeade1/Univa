# apps/backend/biometrics/admin.py

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    BiometricDevice,
    FaceEncoding,
    FaceVerification,
    FaceVerificationImage,
)


@admin.register(BiometricDevice)
class BiometricDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'device_id',
        'trusted',
        'last_used_at',
        'registered_at',
    )
    list_filter = ('trusted', 'registered_at')
    search_fields = ('user__user__email', 'device_id', 'device_info')
    readonly_fields = ('registered_at', 'last_used_at')
    raw_id_fields = ('user',)
    date_hierarchy = 'registered_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'device_id')
        }),
        ('Device Details', {
            'fields': ('device_info', 'biometric_hash')
        }),
        ('Security', {
            'fields': ('public_key', 'trusted')
        }),
        ('Timestamps', {
            'fields': ('last_used_at', 'registered_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['trust_devices', 'revoke_devices']
    
    @admin.action(description="Trust selected devices")
    def trust_devices(self, request, queryset):
        queryset.update(trusted=True)
        self.message_user(request, f"{queryset.count()} device(s) trusted.")
    
    @admin.action(description="Revoke selected devices")
    def revoke_devices(self, request, queryset):
        queryset.update(trusted=False)
        self.message_user(request, f"{queryset.count()} device(s) revoked.")


@admin.register(FaceEncoding)
class FaceEncodingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'version',
        'is_active',
        'created_at',
    )
    list_filter = ('version', 'is_active', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'source_image')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Encoding Data', {
            'fields': ('encoding', 'embedding', 'version')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Source', {
            'fields': ('source_image', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_encodings', 'deactivate_encodings']
    
    @admin.action(description="Activate selected encodings")
    def activate_encodings(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} encoding(s) activated.")
    
    @admin.action(description="Deactivate selected encodings")
    def deactivate_encodings(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} encoding(s) deactivated.")


@admin.register(FaceVerificationImage)
class FaceVerificationImageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'image_preview',
        'is_verified',
        'face_detected',
        'face_count',
        'created_at'
    )
    list_filter = ('is_verified', 'face_detected', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Image', {
            'fields': ('image',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_score', 'face_detected', 'face_count')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    list_editable = ('is_verified',)

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;"/>',
                obj.image.url
            )
        return "-"


@admin.register(FaceVerification)
class FaceVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'is_verified',
        'verification_method',
        'verification_channel',
        'last_verified_at',
        'status',
        'verification_attempts'
    )
    list_filter = ('is_verified', 'verification_method', 'verification_channel')
    search_fields = ('user__email', 'device_id')
    readonly_fields = ('last_verified_at', 'verification_attempts')
    raw_id_fields = ('user',)
    date_hierarchy = 'last_verified_at'
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Verification Status', {
            'fields': ('is_verified', 'verification_method', 'verification_channel')
        }),
        ('Attempts', {
            'fields': ('verification_attempts', 'locked_until')
        }),
        ('Thresholds', {
            'fields': ('confidence_threshold', 'liveness_threshold')
        }),
        ('Device', {
            'fields': ('device_id',)
        }),
        ('Timestamps', {
            'fields': ('last_verified_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_users', 'reset_attempts', 'unlock_users']

    @admin.display(description="Status")
    def status(self, obj):
        if obj.locked_until and obj.locked_until > timezone.now():
            return format_html(
                '<span style="color: red;">🔒 Locked until {}</span>',
                obj.locked_until.strftime("%Y-%m-%d %H:%M"),
            )
        if obj.is_verified:
            return format_html(
                '<span style="color: green;">✅ {}</span>',
                "Verified",
            )
        return format_html(
            '<span style="color: orange;">⏳ {}</span>',
            "Pending",
        )

    @admin.action(description="Mark selected users as verified")
    def verify_users(self, request, queryset):
        queryset.update(
            is_verified=True,
            last_verified_at=timezone.now(),
            verification_attempts=0,
            locked_until=None
        )
        self.message_user(request, f"{queryset.count()} user(s) verified.")

    @admin.action(description="Reset verification attempts")
    def reset_attempts(self, request, queryset):
        queryset.update(
            verification_attempts=0,
            locked_until=None
        )
        self.message_user(request, f"{queryset.count()} user(s) attempts reset.")

    @admin.action(description="Unlock selected users")
    def unlock_users(self, request, queryset):
        queryset.update(locked_until=None)
        self.message_user(request, f"{queryset.count()} user(s) unlocked.")