from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import AuditLog
from .serializers import AuditLogSerializer
from accounts.permissions import IsManagerOrAuditor
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def audit_logs_page(request):
    if not (request.user.is_manager or request.user.is_auditor):
        return render(request, 'dashboard/403.html', status=403)
    return render(request, 'audit/logs.html')

class AuditLogListView(generics.ListAPIView):
    permission_classes = [IsManagerOrAuditor]
    serializer_class = AuditLogSerializer
    pagination_class = None

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    
    filterset_fields = ['action', 'model_name', 'user', 'timestamp']
    search_fields = ['object_id', 'object_display', 'user__email', 'ip_address']
    ordering_fields = ['timestamp', 'action', 'model_name', 'user']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        return AuditLog.objects.select_related('user').all()


class AuditLogDetailView(generics.RetrieveAPIView):
    permission_classes = [IsManagerOrAuditor]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()