# apps/backend/audit/admin.py

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'actor',
        'action',
        'target_user',
        'timestamp',
        'action_icon',
    )
    list_filter = (
        'action',
        'timestamp',
        ('actor', admin.RelatedOnlyFieldListFilter),
        ('target_user', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'action',
        'actor__email',
        'actor__first_name',
        'actor__last_name',
        'target_user__email',
        'target_user__first_name',
        'target_user__last_name',
        'data',
    )
    readonly_fields = ('timestamp', 'formatted_data', 'action_icon_display')
    raw_id_fields = ('actor', 'target_user')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    list_max_show_all = 200
    
    fieldsets = (
        ('Actor Information', {
            'fields': ('actor', 'action', 'action_icon_display')
        }),
        ('Target', {
            'fields': ('target_user',)
        }),
        ('Details', {
            'fields': ('data', 'formatted_data'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('actor', 'target_user')
    
    @admin.display(description="🔹", ordering='action')
    def action_icon(self, obj):
        """Display action with icon based on action type."""
        icons = {
            'login': '🔑',
            'logout': '🚪',
            'create': '➕',
            'update': '✏️',
            'delete': '🗑️',
            'view': '👁️',
            'export': '📤',
            'import': '📥',
            'approve': '✅',
            'reject': '❌',
            'lock': '🔒',
            'unlock': '🔓',
            'reset': '🔄',
            'verify': '✔️',
            'failed': '❌',
            'success': '🎉',
            'error': '⚠️',
        }
        action_lower = obj.action.lower()
        icon = '📋'
        for key, value in icons.items():
            if key in action_lower:
                icon = value
                break
        return format_html('<span title="{}">{}</span>', obj.action, icon)
    
    @admin.display(description="Action Details")
    def formatted_data(self, obj):
        """Display data in a formatted way."""
        if not obj.data:
            return "-"
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; max-height: 300px; overflow: auto;">'
        
        if isinstance(obj.data, dict):
            for key, value in obj.data.items():
                if isinstance(value, (dict, list)):
                    import json
                    html += f'<div><strong>{key}:</strong> <pre style="margin: 5px 0; padding: 5px; background: #eee; border-radius: 3px;">{json.dumps(value, indent=2, default=str)}</pre></div>'
                else:
                    html += f'<div><strong>{key}:</strong> {value}</div>'
        else:
            html += f'<pre>{obj.data}</pre>'
        
        html += '</div>'
        return format_html(html)
    
    @admin.display(description="Action")
    def action_icon_display(self, obj):
        """Display action with icon in detail view."""
        return self.action_icon(obj)
    
    actions = ['delete_selected', 'export_selected']
    
    @admin.action(description="Export selected audit logs")
    def export_selected(self, request, queryset):
        """Export selected audit logs as CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Actor', 'Action', 'Target User', 'Timestamp', 'Data'])
        
        for log in queryset:
            writer.writerow([
                log.id,
                str(log.actor),
                log.action,
                str(log.target_user),
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                str(log.data)
            ])
        
        self.message_user(request, f"Exported {queryset.count()} audit log(s).")
        return response
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but not editing."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion only for superusers."""
        return request.user.is_superuser
    
    class Media:
        css = {
            'all': ('admin/css/audit_log.css',)
        }