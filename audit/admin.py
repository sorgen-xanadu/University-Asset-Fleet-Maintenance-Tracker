from django.contrib import admin
from django.utils.html import format_html
from .models import AuditLog
import json

# Register your models here.
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user_display', 'action_display', 'model_name', 'object_id', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp', 'user']
    search_fields = ['user__email', 'object_id', 'object_display', 'ip_address']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'object_display', 
                       'old_values_formatted', 'new_values_formatted', 'timestamp', 
                       'ip_address', 'user_agent']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def user_display(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'
    user_display.short_description = 'User'
    
    def action_display(self, obj):
        colors = {
            'CREATE': '#28a745',
            'UPDATE': '#ffc107',
            'DELETE': '#dc3545',
            'APPROVE': '#17a2b8',
            'REJECT': '#e83e8c',
            'STATUS_CHANGE': '#007bff',
            'LOGIN': '#20c997',
            'LOGOUT': '#6f42c1',
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = 'Action'
    
    def old_values_formatted(self, obj):
        if not obj.old_values:
            return 'N/A'
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
            json.dumps(obj.old_values, indent=2)
        )
    old_values_formatted.short_description = 'Previous Values'
    
    def new_values_formatted(self, obj):
        if not obj.new_values:
            return 'N/A'
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
            json.dumps(obj.new_values, indent=2)
        )
    new_values_formatted.short_description = 'New Values'
    
    fieldsets = (
        ('Event Details', {
            'fields': ('timestamp', 'user_display', 'action_display')
        }),
        ('Object Changed', {
            'fields': ('model_name', 'object_id', 'object_display')
        }),
        ('Changes', {
            'fields': ('old_values_formatted', 'new_values_formatted')
        }),
        ('Request Context', {
            'fields': ('ip_address', 'user_agent')
        }),
    )