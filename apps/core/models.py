from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import math

class Location(models.Model):
    name = models.CharField(max_length=30, unique=True)
   
    class Meta:
        ordering =['name']
        verbose_name_plural = "locations"        
                        
    def __str__(self):                          
        return self.name

class Venue(models.Model):
    name = models.CharField(max_length=30, unique=True)
    picture = models.ImageField(upload_to="media/venue",null=True)
    location =models.ForeignKey(Location,on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=255,null=True)
    phone = models.IntegerField(null=True)
    email = models.EmailField(null=True)
   
    class Meta:
        ordering =['name']    
                                                
    def __str__(self):                          
        return self.name

class Time(models.Model):
    name = models.CharField(max_length=255,unique=True)

    def __str__(self):                          
        return self.name

class Post(models.Model):
   
    date =models.DateField()
    time = models.ForeignKey(Time,on_delete=models.SET_NULL, null=True)
    venue = models.ForeignKey(Venue,on_delete=models.SET_NULL, null=True)
    location =models.ForeignKey(Location,on_delete=models.SET_NULL, null=True)
    message =models.TextField()
    author = models.ForeignKey(User,on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def whenpublished(self):
        now = timezone.now()
        
        diff= now - self.created_at

        if diff.days == 0 and diff.seconds >= 0 and diff.seconds < 60:
            seconds= diff.seconds
            
            if seconds == 1:
                return str(seconds) +  "second ago"
            
            else:
                return str(seconds) + " seconds ago"

            

        if diff.days == 0 and diff.seconds >= 60 and diff.seconds < 3600:
            minutes= math.floor(diff.seconds/60)

            if minutes == 1:
                return str(minutes) + " minute ago"
            
            else:
                return str(minutes) + " minutes ago"



        if diff.days == 0 and diff.seconds >= 3600 and diff.seconds < 86400:
            hours= math.floor(diff.seconds/3600)

            if hours == 1:
                return str(hours) + " hour ago"

            else:
                return str(hours) + " hours ago"

        # 1 day to 30 days
        if diff.days >= 1 and diff.days < 30:
            days= diff.days
        
            if days == 1:
                return str(days) + " day ago"

            else:
                return str(days) + " days ago"

        if diff.days >= 30 and diff.days < 365:
            months= math.floor(diff.days/30)
            

            if months == 1:
                return str(months) + " month ago"

            else:
                return str(months) + " months ago"


        if diff.days >= 365:
            years= math.floor(diff.days/365)

            if years == 1:
                return str(years) + " year ago"

            else:
                return str(years) + " years ago"
            
class Contact(models.Model):
    fullname = models.CharField(max_length=255,null=False)
    phone = models.BigIntegerField(null=False)
    email = models.EmailField(null=False)
    message = models.TextField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
    class Meta:
        ordering =['created_at']    
                                                
    def __str__(self):                          
        return self.fullname

