# admin.py

from django.contrib import admin
from django.contrib.admin import display
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from support.models.contact import ContactUs


@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    """
    Admin interface for ContactUs model.
    
    Features:
        - List view with key information
        - Search by name, email, message
        - Filter by replied status and date
        - Inline reply form
        - Export action
        - Mark as replied/unreplied actions
        - Read-only detail view for message
    """
    
    # =========================================================================
    # List View Configuration
    # =========================================================================
    
    list_display = (
        "name",
        "email",
        "created_at_display",
        "message_preview",
        "replied_status",
        "replied_at_display",
        "replied_by_display",
    )
    
    list_filter = (
        "replied",
        "created_at",
        "replied_at",
    )
    
    search_fields = (
        "name",
        "email",
        "message",
        "reply_message",
    )
    
    ordering = ("-created_at",)
    
    date_hierarchy = "created_at"
    
    list_per_page = 25
    
    # =========================================================================
    # Detail Form Configuration
    # =========================================================================
    
    fieldsets = (
        ("Contact Information", {
            "fields": (
                "name",
                "email",
                "message",
                "created_at_readonly",
            ),
            "classes": ("wide",),
        }),
        ("Reply Information", {
            "fields": (
                "replied",
                "reply_message",
                "replied_by",
                "replied_at_readonly",
            ),
            "classes": ("wide",),
        }),
    )
    
    readonly_fields = (
        "created_at_readonly",
        "replied_at_readonly",
    )
    
    # =========================================================================
    # Inline Reply Form
    # =========================================================================
    
    # Custom form to handle replies inline
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        if obj and obj.replied:
            # If already replied, make reply fields read-only
            reply_fields = ["reply_message", "replied_by", "replied_at_readonly"]
            for field in reply_fields:
                if field in form.base_fields:
                    form.base_fields[field].disabled = True
                    form.base_fields[field].help_text = "This reply is already sent."
        
        return form
    
    # =========================================================================
    # Custom Display Methods
    # =========================================================================
    
    @display(description="Created", ordering="created_at")
    def created_at_display(self, obj):
        """Display created_at in a human-readable format."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    
    @display(description="Replied At", ordering="replied_at")
    def replied_at_display(self, obj):
        """Display replied_at if set."""
        if obj.replied_at:
            return obj.replied_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    @display(description="Replied By")
    def replied_by_display(self, obj):
        """Display replied_by user."""
        if obj.replied_by:
            url = reverse(
                "admin:auth_user_change",
                args=[obj.replied_by.pk]
            )
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.replied_by.email
            )
        return "-"
    
    @display(description="Message", ordering="message")
    def message_preview(self, obj):
        """Display a truncated preview of the message."""
        if len(obj.message) > 50:
            return f"{obj.message[:50]}..."
        return obj.message
    
    @display(description="Status", boolean=True)
    def replied_status(self, obj):
        """Display replied status as a boolean."""
        return obj.replied
    
    @display(description="Created At", ordering="created_at")
    def created_at_readonly(self, obj):
        """Read-only version for the detail view."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    
    @display(description="Replied At", ordering="replied_at")
    def replied_at_readonly(self, obj):
        """Read-only version for the detail view."""
        if obj.replied_at:
            return obj.replied_at.strftime("%Y-%m-%d %H:%M:%S")
        return "Not replied yet"
    
    # =========================================================================
    # Actions
    # =========================================================================
    
    actions = (
        "mark_as_replied",
        "mark_as_unreplied",
        "export_selected",
    )
    
    @admin.action(
        description="Mark selected contacts as replied"
    )
    def mark_as_replied(self, request, queryset):
        """Mark selected contact submissions as replied."""
        count = queryset.update(
            replied=True,
            replied_at=timezone.now(),
            replied_by=request.user,
        )
        self.message_user(
            request,
            f"Successfully marked {count} contact(s) as replied."
        )
    
    @admin.action(
        description="Mark selected contacts as unreplied"
    )
    def mark_as_unreplied(self, request, queryset):
        """Mark selected contact submissions as unreplied."""
        count = queryset.update(
            replied=False,
            replied_at=None,
            replied_by=None,
            reply_message=None,
        )
        self.message_user(
            request,
            f"Successfully marked {count} contact(s) as unreplied."
        )
    
    @admin.action(
        description="Export selected contacts to CSV"
    )
    def export_selected(self, request, queryset):
        """
        Export selected contact submissions to CSV.
        """
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="contacts_export.csv"'
        )
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            "ID",
            "Name",
            "Email",
            "Message",
            "Created At",
            "Replied",
            "Replied At",
            "Reply Message",
        ])
        
        # Write data
        for contact in queryset:
            writer.writerow([
                str(contact.id),
                contact.name,
                contact.email,
                contact.message,
                contact.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Yes" if contact.replied else "No",
                contact.replied_at.strftime("%Y-%m-%d %H:%M:%S") if contact.replied_at else "",
                contact.reply_message or "",
            ])
        
        self.message_user(request, f"Exported {queryset.count()} contacts.")
        return response
    
    # =========================================================================
    # Save / Reply Handling
    # =========================================================================
    
    def save_model(self, request, obj, form, change):
        """
        Handle reply logic when saving the model.
        """
        if obj.replied and not obj.replied_at:
            # First time replying
            obj.replied_at = timezone.now()
            obj.replied_by = request.user
        
        if not obj.replied:
            # If unreplied, clear reply fields
            obj.replied_at = None
            obj.replied_by = None
            obj.reply_message = None
        
        super().save_model(request, obj, form, change)
    
    # =========================================================================
    # QuerySet Optimization
    # =========================================================================
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for replied_by."""
        return super().get_queryset(request).select_related("replied_by")
    
    # =========================================================================
    # Permissions / Customization
    # =========================================================================
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields read-only based on state."""
        if obj and obj.replied:
            # If already replied, make message read-only
            return self.readonly_fields + ("message",)
        return self.readonly_fields
    
    # =========================================================================
    # Statistics / Dashboard (Optional)
    # =========================================================================
    
    def changelist_view(self, request, extra_context=None):
        """Add statistics to the changelist view."""
        extra_context = extra_context or {}
        
        # Get statistics
        total = ContactUs.objects.count()
        replied = ContactUs.objects.filter(replied=True).count()
        unreplied = ContactUs.objects.filter(replied=False).count()
        
        extra_context.update({
            "total_contacts": total,
            "replied_count": replied,
            "unreplied_count": unreplied,
            "reply_rate": f"{(replied / total * 100):.1f}%" if total > 0 else "0%",
        })
        
        return super().changelist_view(request, extra_context=extra_context)


# =========================================================================
# Optional: Inline Admin for related models
# =========================================================================

# If you want to show contact replies in the user admin:
class UserContactRepliesInline(admin.TabularInline):
    model = ContactUs
    fk_name = "replied_by"
    fields = (
        "name",
        "email",
        "created_at",
        "replied_at",
    )
    readonly_fields = fields
    extra = 0
    max_num = 0
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# To add to UserAdmin (in your main admin.py):
# from django.contrib.auth.admin import UserAdmin
# UserAdmin.inlines = UserAdmin.inlines + [UserContactRepliesInline]