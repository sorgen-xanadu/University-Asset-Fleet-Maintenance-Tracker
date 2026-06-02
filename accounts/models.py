from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


# Create your models here.
class Role(models.TextChoices):
    STAFF   = 'STAFF',   'Standard Staff'
    AUDITOR = 'AUDITOR', 'Auditor (Read Only)'
    MANAGER = 'MANAGER', 'Motorpool Manager'


class UserManager(BaseUserManager):

    def _create_user (self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self,email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', Role.STAFF)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self,email,password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Role.MANAGER)
        return self._create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50,blank=True, null=True, unique=True)
    department = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(
                    max_length=10,
                    choices=Role.choices,
                    default=Role.STAFF,
                    db_index=True,
                    )
    
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)


    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'User'
        verbose_name_plural = 'Users'
        ordering            = ['last_name', 'first_name']

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return f'{self.get_full_name()} <{self.email}> [{self.role}]'

    
    @property
    def is_manager(self):
        return self.role == Role.MANAGER

    @property
    def is_auditor(self):
        return self.role == Role.AUDITOR

    @property
    def is_standard_staff(self):
        return self.role == Role.STAFF

    @property
    def can_view_costs(self):
        return self.role == Role.MANAGER

    @property
    def can_approve_requests(self):
        return self.role == Role.MANAGER

    @property
    def can_create_work_orders(self):
        return self.role == Role.MANAGER

    @property
    def is_read_only(self):
        return self.role == Role.AUDITOR

