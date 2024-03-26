from django.db import models
from django.contrib.auth.models import User
from phone_field import PhoneField
from PIL import Image

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_image = models.ImageField(default='media/profile_pics/default.jpg', upload_to='media/profile_pics')
    cover_image = models.ImageField(default='media/cover_pics/cover.jpg', upload_to='media/cover_pics')
    phone = PhoneField(blank=True, help_text='Contact phone number', null=True)
    address = models.CharField(max_length=50, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

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