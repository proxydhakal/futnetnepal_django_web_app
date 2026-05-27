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
        self.save(update_fields=['email_verified', 'email_verification_token'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.profile_image.path)
        cov = Image.open(self.cover_image.path)

        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.profile_image.path)
        else:
            img.save(self.profile_image.path)

        if cov.height > 650 or cov.width > 1650:
            output_size = (650, 1650)
            cov.resize(output_size)
            cov.save(self.cover_image.path)