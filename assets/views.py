from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Asset, AssetCategory
from accounts.permissions import IsManager, IsManagerOrReadOnly
from .serializers import AssetCategorySerializer, StaffAssetSerializer, ManagerAssetSerializer
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from audit.utils import log_action

class AssetCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsManagerOrReadOnly]
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer

class AssetListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsManagerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Asset.objects.all()

        # Filter by category if provided
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__name__icontains=category)

        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(current_status=status_filter)

        return queryset

#    def perform_create(self, serializer):
#       serializer.save(created_by=self.request.user)

    def perform_create(self, serializer):
        asset = serializer.save(created_by=self.request.user)

        log_action(
            user=self.request.user,
            action='CREATE',
            model_name='Asset',
            object_id=asset.id,
            object_display=f'{asset.asset_name} [{asset.current_status}]',
            new_values={
                'asset_name': asset.asset_name,
                'serial_number': asset.serial_number,
                'category': asset.category.name,
            },
            request=self.request
        )

    def get_serializer_class(self):
        user = self.request.user

        if user.is_manager:     
            return ManagerAssetSerializer  

        return StaffAssetSerializer

class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsManagerOrReadOnly]

    def get_queryset(self):
        return Asset.objects.all()

    def get_object(self):
        queryset = self.get_queryset()
        obj = queryset.filter(pk=self.kwargs['pk']).first()

        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound('Asset not found.')

        return obj

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.current_status == Asset.Status.UNDER_MAINTENANCE:
            return Response(
                {'detail': 'Cannot delete an asset that is under maintenance.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = obj.current_status

        obj.current_status = Asset.Status.RETIRED
        obj.save()

        log_action(
            user=request.user,
            action='STATUS_CHANGE',
            model_name='Asset',
            object_id=obj.id,
            object_display=f'{obj.asset_name} [RETIRED]',
            old_values={'current_status': old_status},
            new_values={'current_status': Asset.Status.RETIRED},
            request=request
        )

        return Response(
            {'detail': f'{obj.asset_name} has been retired.'},
            status=status.HTTP_200_OK
        )
    


    def get_serializer_class(self):
        user = self.request.user
        
        if user.is_manager:     
            return ManagerAssetSerializer  

        return StaffAssetSerializer
        
@login_required(login_url='/login/')
def assets_page(request):
    return render(request, 'assets/assets.html')