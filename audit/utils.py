from .models import AuditLog
import json
from decimal import Decimal


def get_client_ip(request):
    """Extract client IP from request, accounting for proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def serialize_value(value):
    """Convert Django model instances and other types to JSON-serializable format."""
    if isinstance(value, Decimal):
        return float(value)
    elif hasattr(value, 'id'):  # Django model instance
        return f'{value.__class__.__name__}:{value.id}'
    elif isinstance(value, (list, dict)):
        return value
    return str(value)


def capture_changes(instance):
    """
    Compare instance with database to identify what changed.
    Returns: (old_values_dict, new_values_dict, changed_fields_list)
    """
    from django.db.models import Model
    
    if not isinstance(instance, Model):
        return None, None, []
    
    try:
        db_instance = instance.__class__.objects.get(pk=instance.pk)
        old_values = {}
        new_values = {}
        changed_fields = []
        
        for field in instance._meta.get_fields():
            # Skip relations and private fields
            if field.many_to_one or field.one_to_many or field.many_to_many:
                continue
            if field.name.startswith('_'):
                continue
            
            old_val = getattr(db_instance, field.name)
            new_val = getattr(instance, field.name)
            
            if old_val != new_val:
                changed_fields.append(field.name)
                old_values[field.name] = serialize_value(old_val)
                new_values[field.name] = serialize_value(new_val)
        
        return old_values if changed_fields else None, new_values if changed_fields else None, changed_fields
    except instance.__class__.DoesNotExist:
        # New object
        return None, None, []


def log_action(user, action, model_name, object_id, object_display='', 
               old_values=None, new_values=None, request=None):
    """
    Log an audit event.
    
    Args:
        user: User performing the action (can be None for system actions)
        action: One of ACTION_CHOICES ('CREATE', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT', 'STATUS_CHANGE')
        model_name: Model being affected (e.g., 'MaintenanceRequest')
        object_id: Primary key of affected object
        object_display: Human-readable description of the object
        old_values: Dict of previous field values
        new_values: Dict of new field values
        request: HTTP request object (for IP and user agent)
    """
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    log_entry = AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_display=object_display[:255],
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return log_entry


def log_model_change(user, instance, action, request=None, old_values=None, new_values=None):
    """
    Convenience function to log changes to a model instance.
    Automatically captures old/new values if not provided.
    """
    if not old_values or not new_values:
        old_vals, new_vals, _ = capture_changes(instance)
        old_values = old_values or old_vals
        new_values = new_values or new_vals
    
    return log_action(
        user=user,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.id,
        object_display=str(instance),
        old_values=old_values,
        new_values=new_values,
        request=request,
    )