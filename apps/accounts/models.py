import os
import secrets

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_image = models.ImageField(default='media/profile_pics/default.jpg', upload_to='media/profile_pics')
    cover_image = models.ImageField(default='media/cover_pics/cover.jpg', upload_to='media/cover_pics')
    phone = models.CharField(max_length=10, blank=True, default='', help_text='10-digit contact number')
    address = models.CharField(max_length=50, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)
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

    def ensure_verification_token(self):
        if not self.email_verification_token:
            self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token

    def mark_email_verified(self):
        self.email_verified = True
        self.email_verification_token = ''
        self.email_otp_hash = ''
        self.email_otp_attempts = 0
        self.save(update_fields=[
            'email_verified', 'email_verification_token', 'email_otp_hash', 'email_otp_attempts',
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
            if not {'profile_image', 'cover_image'} & set(update_fields):
                return
        self._resize_image_file(self.profile_image, (300, 300))
        self._resize_image_file(self.cover_image, (1650, 650))
