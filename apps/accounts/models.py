import os
import secrets

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    Permission,
    PermissionsMixin,
)
from django.conf import settings
from django.db import models
from django.utils import timezone
from PIL import Image

from futnetnepal.audit import _valid_audit_user, get_audit_user
from futnetnepal.models import TimestampedSoftDeleteModel


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address.')
        if not username:
            raise ValueError('User must have a username.')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)
        extra_fields.setdefault('status', User.Status.ACTIVE)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, password, **extra_fields)


class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.IntegerChoices):
        SUPER_ADMIN = 0, 'Super Admin'
        USER = 1, 'User'
        VENDOR = 2, 'Vendor'

    class Status(models.TextChoices):
        INACTIVE = 'INACTIVE', 'Inactive'
        ACTIVE = 'ACTIVE', 'Active'
        DELETED = 'DELETED', 'Deleted'

    role = models.IntegerField(choices=Role.choices, default=Role.USER)
    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=255, unique=True)
    full_name = models.CharField(max_length=255, blank=True, default='')
    profile_image = models.ImageField(
        default='profile_pics/default.jpg',
        upload_to='profile_pics',
    )
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounts_created',
    )
    updated_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounts_updated',
    )
    deleted_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounts_deleted',
    )

    objects = ActiveUserManager()
    all_objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    groups = models.ManyToManyField(
        Group,
        related_name='useraccount_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='useraccount_set',
        blank=True,
    )

    class Meta:
        db_table = 'accounts_useraccount'
        verbose_name = 'user account'
        verbose_name_plural = 'user accounts'

    def __str__(self):
        return self.username

    def get_full_name(self):
        return (self.full_name or '').strip() or self.username

    def get_short_name(self):
        name = (self.full_name or '').strip()
        if name:
            return name.split()[0]
        return self.username

    @property
    def first_name(self):
        parts = (self.full_name or '').split(None, 1)
        return parts[0] if parts else ''

    @property
    def last_name(self):
        parts = (self.full_name or '').split(None, 1)
        return parts[1] if len(parts) > 1 else ''

    @property
    def date_joined(self):
        return self.created_at

    def save(self, *args, **kwargs):
        if self.role == self.Role.SUPER_ADMIN:
            self.is_superuser = True
            self.is_staff = True
        if self.email and not self.profile_image:
            email_prefix = self.email.split('@')[0] if '@' in self.email else 'default'
            self.profile_image.name = f'media/profile_pics/{email_prefix}.png'
        audit = get_audit_user()
        if _valid_audit_user(audit):
            if self._state.adding and not self.created_by_id:
                self.created_by = audit
            elif not self._state.adding:
                self.updated_by = audit
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.status = self.Status.DELETED
        self.is_active = False
        update_fields = ['is_deleted', 'deleted_at', 'status', 'is_active']
        audit = get_audit_user()
        if _valid_audit_user(audit):
            self.deleted_by = audit
            update_fields.append('deleted_by')
        self.save(update_fields=update_fields)

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.status = self.Status.ACTIVE
        self.is_active = True
        self.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by', 'status', 'is_active',
        ])


UserAccount = User


class Profile(TimestampedSoftDeleteModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    cover_image = models.ImageField(
        default='cover_pics/cover.jpg',
        upload_to='cover_pics',
    )
    phone = models.CharField(max_length=10, blank=True, default='', help_text='10-digit contact number')
    address = models.CharField(max_length=50, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    email_verification_token = models.CharField(max_length=64, blank=True, db_index=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    email_otp_hash = models.CharField(max_length=128, blank=True)
    email_otp_attempts = models.PositiveSmallIntegerField(default=0)
    phone_verified = models.BooleanField(default=False)
    phone_otp_hash = models.CharField(max_length=128, blank=True)
    phone_otp_sent_at = models.DateTimeField(null=True, blank=True)
    phone_otp_attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def email_verified(self):
        return self.user.is_email_verified

    @property
    def profile_image(self):
        return self.user.profile_image

    def ensure_verification_token(self):
        if not self.email_verification_token:
            self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token

    def mark_email_verified(self):
        self.user.is_email_verified = True
        self.user.save(update_fields=['is_email_verified'])
        self.email_verification_token = ''
        self.email_otp_hash = ''
        self.email_otp_attempts = 0
        self.save(update_fields=[
            'email_verification_token', 'email_otp_hash', 'email_otp_attempts',
        ])

    def _resize_image_file(self, field, max_size):
        if not field or not field.name:
            return
        try:
            path = field.path
        except (ValueError, FileNotFoundError):
            return
        if not os.path.isfile(path):
            return
        with Image.open(path) as img:
            if img.height > max_size[1] or img.width > max_size[0]:
                img.thumbnail(max_size)
            img.save(path)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            if 'cover_image' not in set(update_fields):
                return
        self._resize_image_file(self.cover_image, (1650, 650))
