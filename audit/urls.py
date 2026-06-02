from django.urls import path
from .views import AuditLogListView, AuditLogDetailView, audit_logs_page

app_name = 'audit'

urlpatterns = [
    path('logs/', audit_logs_page, name='logs-page'),
    path('', AuditLogListView.as_view(), name='auditlog-list'),
    path('<int:pk>/', AuditLogDetailView.as_view(), name='auditlog-detail'),
]