from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.conf import settings
from PIL import Image
from phone_field import PhoneField

# Create your models here.



# class User(AbstractUser):
#     ROLES=(("0", "Admin"), ("1", "User"), ("2", "Guest"))
#     role = models.CharField(max_length=1, choices=ROLES, default=2)
#     email = models.EmailField(_('email address'), unique=True)


#     USERNAME_FIELD = "email"
#     REQUIRED_FIELDS= "username",

class Profile(models.Model):
    user= models.OneToOneField(User, on_delete=models.CASCADE, related_name="profiles")
    profile_image=models.ImageField(default='default.jpg',upload_to='media/profile_pics')
    cover_image=models.ImageField(default='cover.jpg',upload_to='media/cover_pics')
    phone = PhoneField(blank=True, help_text='Contact phone number')
    address= models.CharField(max_length=50, blank=True)
    dob= models.DateField(blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'


    def save(self, *args, **kawrgs):
        super().save(*args, **kawrgs)

        img = Image.open(self.profile_image.path)
        cov =Image.open(self.cover_image.path)

        if img.height > 300 or img.width> 300:
            output_size =(300,300)
            img.thumbnail(output_size)
            img.save(self.profile_image.path)
        else:
            img.save(self.profile_image.path)

        if cov.height >650 or cov.width >1650:
            output_size =(650,1650)
            cov.resize(output_size)
            cov.save(self.cover_image.path)