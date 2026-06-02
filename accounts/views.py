from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserManagementSerializer, CreateUserSerializer
from .permissions import IsManager
from audit.utils import log_action

class UserListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsManager]

    def get_queryset(self):
        return User.objects.all().order_by('last_name')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateUserSerializer
        return UserManagementSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()

        # Log user creation
        log_action(
            user=self.request.user,
            action='CREATE',
            model_name='User',
            object_id=user.id,
            object_display=f'{user.get_full_name()} ({user.email}) - Role: {user.get_role_display()}',
            new_values={
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
            },
            request=self.request
        )

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    error = None
    if request.method == 'POST':
        email    = request.POST.get('email')
        password = request.POST.get('password')
        user     = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)

            # Log successful login
            log_action(
                user=user,
                action='LOGIN',
                model_name='User',
                object_id=user.id,
                object_display=f'{user.get_full_name()} ({user.email})',
                request=request
            )

            return redirect('dashboard')
        else:
            error = 'Invalid email or password.'

    return render(request, 'accounts/login.html', {'error': error})


def logout_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)

        # Log logout action
        log_action(
            user=user,
            action='LOGOUT',
            model_name='User',
            object_id=user.id,
            object_display=f'{user.get_full_name()} ({user.email})',
            request=request
        )

        return redirect('login')


@login_required(login_url='/login/')
def users_page(request):
    return render(request, 'accounts/users.html')