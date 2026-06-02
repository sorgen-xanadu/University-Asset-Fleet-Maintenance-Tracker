from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'timestamp',
            'user',
            'user_name',
            'user_email',
            'action',
            'action_display',
            'model_name',
            'object_id',
            'object_display',
            'old_values',
            'new_values',
            'ip_address',
        ]
        read_only_fields = fields