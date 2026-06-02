from audit.utils import log_action
from rest_framework import generics, status
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import MaintenanceRequest, WorkOrder, MaintenanceHistory
from accounts.permissions import IsManager, IsManagerOrAuditor
from .serializers import (
    MaintenanceRequestSerializer,
    WorkOrderSerializer,
    StaffMaintenanceHistorySerializer,
    ManagerMaintenanceHistorySerializer,
)


class MaintenanceRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MaintenanceRequestSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_manager or user.is_auditor:
            return MaintenanceRequest.objects.all()
        
        return MaintenanceRequest.objects.filter(requested_by=user)

    # def perform_create(self, serializer):
    #     if self.request.user.is_read_only:
    #         return Response(
    #             {'detail': 'Auditors cannot submit requests.'},
    #             status=status.HTTP_403_FORBIDDEN
    #         )
    #     serializer.save(requested_by=self.request.user)

    # The above code is changed to this; we want to raise an exception instead of returning a response, since perform_create is not designed to return HTTP responses.
    def perform_create(self, serializer):
        if self.request.user.is_read_only:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Auditors cannot submit requests.')
        serializer.save(requested_by=self.request.user)


class MaintenanceRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MaintenanceRequestSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_manager or user.is_auditor:
            return MaintenanceRequest.objects.all()

        return MaintenanceRequest.objects.filter(requested_by=user)

    def get_object(self):
        queryset = self.get_queryset()
        obj = queryset.filter(pk=self.kwargs['pk']).first()

        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound('Request not found.')

        return obj

# NEW CODE: Override update to log status changes
    def perform_update(self, serializer):
        request_obj = self.get_object()
        old_status = request_obj.status

        serializer.save()

        new_status = serializer.instance.status
        if old_status != new_status:
            log_action(
                user=self.request.user,
                action='STATUS_CHANGE',
                model_name='MaintenanceRequest',
                object_id=request_obj.id,
                object_display=f'{request_obj.asset.asset_name} - {new_status}',
                old_values={'status': old_status},
                new_values={'status': new_status},
                request=self.request
            )
# END OF NEW CODE

class BulkUpdateRequestStatusView(generics.GenericAPIView):
    permission_classes = [IsManager]

    def post(self, request):
        request_ids = request.data.get('request_ids', [])
        new_status  = request.data.get('status', None)

        if not request_ids or not new_status:
            return Response(
                {'detail': 'request_ids and status are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_statuses = [
            MaintenanceRequest.Status.APPROVED,
            MaintenanceRequest.Status.REJECTED,
            MaintenanceRequest.Status.COMPLETED,
        ]

        if new_status not in valid_statuses:
            return Response(
                {'detail': f'Invalid status. Choose from {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        requests_to_update = MaintenanceRequest.objects.filter(id__in=request_ids)

        for req in requests_to_update:
            log_action(
                user=request.user,
                action='STATUS_CHANGE',
                model_name='MaintenanceRequest',
                object_id=req.id,
                object_display=f'{req.asset.asset_name} - {new_status}',
                old_values={'status': req.status},
                new_values={'status': new_status},
                request=request
            )

        updated = MaintenanceRequest.objects.filter(
            id__in=request_ids
        ).update(status=new_status)

        return Response({
            'detail': f'{updated} requests updated to {new_status}.'
        }, status=status.HTTP_200_OK)


class WorkOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkOrderSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_manager or user.is_auditor:
            return WorkOrder.objects.all()

        return WorkOrder.objects.filter(
            maintenance_request__requested_by=user
        )

    def perform_create(self, serializer):
        if not self.request.user.is_manager:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only Managers can create work orders.')
        
        work_order = serializer.save()
    
        # Automatically set asset to UNDER_MAINTENANCE
        asset = work_order.maintenance_request.asset
        asset.current_status = 'UNDER_MAINTENANCE'
        asset.save()


class WorkOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkOrderSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_manager or user.is_auditor:
            return WorkOrder.objects.all()

        return WorkOrder.objects.filter(
            maintenance_request__requested_by=user
        )

    def get_object(self):
        queryset = self.get_queryset()
        obj = queryset.filter(pk=self.kwargs['pk']).first()

        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound('Work order not found.')

        return obj

    def update(self, request, *args, **kwargs):
        partial  = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)

        new_status = request.data.get('status', None)
        asset      = instance.maintenance_request.asset

        if new_status in ('COMPLETED', 'CANCELLED'):
            asset.current_status = 'ACTIVE'
            asset.save()

            if new_status == 'COMPLETED':
                maintenance_cost = request.data.get('maintenance_cost', 0)
                remarks          = request.data.get('remarks', '')

                MaintenanceHistory.objects.create(
                    asset            = asset,
                    work_order       = instance,
                    maintenance_cost = maintenance_cost,
                    remarks          = remarks,
                    completed_by     = request.user,
                )

        serializer.save()

        # LOGGING STATUS CHANGE
        if old_status != new_status:
            log_action(
                user=request.user,
                action='STATUS_CHANGE',
                model_name='WorkOrder',
                object_id=instance.id,
                object_display=f'WO-{instance.id} - {new_status}',
                old_values={'status': old_status},
                new_values={'status': new_status},
                request=request
            )
    
        return Response(serializer.data)
    
class MaintenanceHistoryListView(generics.ListAPIView):
    permission_classes = [IsManagerOrAuditor]

    def get_serializer_class(self):
        if self.request.user.is_manager:
            return ManagerMaintenanceHistorySerializer
        return StaffMaintenanceHistorySerializer
    
    def get_queryset(self):
        user = self.request.user

        if user.is_manager or user.is_auditor:
            return MaintenanceHistory.objects.all()

        return MaintenanceHistory.objects.filter(
            asset__maintenance_requests__requested_by=user
        )

@login_required(login_url='/login/')
def requests_page(request):
    return render(request, 'maintenance/requests.html')

@login_required(login_url='/login/')
def workorders_page(request):
    return render(request, 'maintenance/workorders.html')

@login_required(login_url='/login/')
def history_page(request):
    return render(request, 'maintenance/history.html')