from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT Auth
    path('api/auth/login/',   TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('api/auth/logout/',  TokenBlacklistView.as_view(),   name='token_blacklist'),

    # API endpoints
    path('api/assets/',      include('assets.urls')),
    path('api/maintenance/', include('maintenance.urls')),
    path('api/dashboard/',   include('dashboard.urls')),
    path('api/accounts/',    include('accounts.urls')),
    path('api/audit/',       include('audit.urls')), 

    # Frontend
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),

    # Root redirect
    path('', RedirectView.as_view(url='/login/')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)