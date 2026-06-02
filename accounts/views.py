from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserManagementSerializer, CreateUserSerializer
from .permissions import IsManager
from audit.utils import log_action
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

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
        
        try:
            user = User.objects.get(email=email)
            if user.locked_until and user.locked_until > timezone.now():
                remaining_time = user.locked_until - timezone.now()
                minutes = int(remaining_time.total_seconds() / 60)
                error = f'Account locked due to multiple failed login attempts. Try again in {minutes} minutes.'
        except User.DoesNotExist:
            pass
        
        if not error:
            user = authenticate(request, username=email, password=password)

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


User = get_user_model()

class FailedLoginTrackingBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None

        # Check if account is locked
        if user.locked_until and user.locked_until > timezone.now():
            if request:
                log_action(
                    user=user,
                    action='LOGIN',
                    model_name='User',
                    object_id=user.id,
                    object_display=f'{user.get_full_name()} - LOCKED ACCOUNT ATTEMPT',
                    request=request
                )
            return None

        # Verify password
        if user.check_password(password) and self.user_can_authenticate(user):
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])

            # Log successful login
            if request:
                log_action(
                    user=user,
                    action='LOGIN',
                    model_name='User',
                    object_id=user.id,
                    object_display=f'{user.get_full_name()} ({user.email})',
                    request=request
                )

            return user
        else:
            # Increment failed attempts
            user.failed_login_attempts += 1
            user.last_failed_login = timezone.now()

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = timezone.now() + timedelta(minutes=30)

            user.save(update_fields=['failed_login_attempts', 'last_failed_login', 'locked_until'])

            # Log failed attempt
            if request:
                log_action(
                    user=user,
                    action='LOGIN',
                    model_name='User',
                    object_id=user.id,
                    object_display=f'{user.get_full_name()} - FAILED ATTEMPT #{user.failed_login_attempts}',
                    request=request
                )

            return None