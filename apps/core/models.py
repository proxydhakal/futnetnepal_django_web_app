from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import math

from apps.core.slugs import make_slug

class Location(models.Model):
    name = models.CharField(max_length=30, unique=True)
   
    class Meta:
        ordering =['name']
        verbose_name_plural = "locations"        
                        
    def __str__(self):                          
        return self.name

class Venue(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    picture = models.ImageField(upload_to="media/venue",null=True)
    location =models.ForeignKey(Location,on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=255,null=True)
    phone = models.IntegerField(null=True)
    email = models.EmailField(null=True)
   
    class Meta:
        ordering =['name']    
                                                
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.name, Venue, instance_pk=self.pk, max_length=60)
        super().save(*args, **kwargs)


class Time(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.name, Time, instance_pk=self.pk, max_length=80)
        super().save(*args, **kwargs)


class Post(models.Model):
    STATUS_OPEN = 'open'
    STATUS_DISCUSSING = 'discussing'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    EVENT_STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_DISCUSSING, 'Discussing'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    slug = models.SlugField(max_length=80, unique=True, blank=True)
    event_status = models.CharField(
        max_length=20, choices=EVENT_STATUS_CHOICES, default=STATUS_OPEN,
    )
    date =models.DateField()
    time = models.ForeignKey(Time,on_delete=models.SET_NULL, null=True)
    venue = models.ForeignKey(Venue,on_delete=models.SET_NULL, null=True)
    location =models.ForeignKey(Location,on_delete=models.SET_NULL, null=True)
    message =models.TextField()
    author = models.ForeignKey(User,on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = (self.message or 'event')[:50]
            self.slug = make_slug(base, Post, instance_pk=self.pk, max_length=80)
        super().save(*args, **kwargs)

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


class VenueBooking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='venue_bookings')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    time_slot = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} · {self.venue.name} · {self.booking_date}'

    def display_time(self):
        if self.preferred_time:
            return self.preferred_time.strftime('%I:%M %p').lstrip('0')
        if self.time_slot_id:
            return str(self.time_slot)
        return 'Any time'


class PostInterest(models.Model):
    STATUS_INTERESTED = 'interested'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_DECLINED = 'declined'
    PARTICIPATION_CHOICES = [
        (STATUS_INTERESTED, 'Interested'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_DECLINED, 'Declined'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='interests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_interests')
    participation_status = models.CharField(
        max_length=20, choices=PARTICIPATION_CHOICES, default=STATUS_INTERESTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['post', 'user']]


class PostReaction(models.Model):
    REACTION_LIKE = 'like'
    REACTION_CHOICES = [(REACTION_LIKE, 'Like')]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES, default=REACTION_LIKE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['post', 'user', 'reaction_type']]


class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.user.username} on post {self.post_id}'


class Notification(models.Model):
    TYPE_INTEREST = 'interest'
    TYPE_LIKE = 'like'
    TYPE_COMMENT = 'comment'
    TYPE_REPLY = 'reply'
    TYPE_CHAT = 'chat'
    TYPE_BOOKING = 'booking'
    TYPE_CHOICES = [
        (TYPE_INTEREST, 'Interested'),
        (TYPE_LIKE, 'Like'),
        (TYPE_COMMENT, 'Comment'),
        (TYPE_REPLY, 'Reply'),
        (TYPE_CHAT, 'Chat'),
        (TYPE_BOOKING, 'Booking'),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications',
    )
    actor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications_sent', null=True, blank=True,
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True,
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username}: {self.message[:40]}'


class DirectConversation(models.Model):
    """Private 1:1 thread between two users about one event."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='direct_conversations')
    user_a = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='dm_conversations_as_a',
    )
    user_b = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='dm_conversations_as_b',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user_a', 'user_b'],
                name='uniq_dm_per_post_pair',
            ),
        ]
        ordering = ['-updated_at']

    def other_user(self, user):
        if user.pk == self.user_a_id:
            return self.user_b
        return self.user_a

    def involves_user(self, user_id):
        return user_id in (self.user_a_id, self.user_b_id)

    def __str__(self):
        return f'DM {self.user_a_id}↔{self.user_b_id} · post {self.post_id}'


class EventChatMessage(models.Model):
    TYPE_TEXT = 'text'
    TYPE_SYSTEM = 'system'
    TYPE_ATTENDANCE = 'attendance'
    TYPE_EVENT_CONFIRMED = 'event_confirmed'
    MESSAGE_TYPE_CHOICES = [
        (TYPE_TEXT, 'Text'),
        (TYPE_SYSTEM, 'System'),
        (TYPE_ATTENDANCE, 'Attendance'),
        (TYPE_EVENT_CONFIRMED, 'Event confirmed'),
    ]

    conversation = models.ForeignKey(
        DirectConversation, on_delete=models.CASCADE, related_name='messages',
        null=True, blank=True,
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='event_chat_messages',
        null=True, blank=True,
    )
    body = models.TextField(max_length=1000)
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPE_CHOICES, default=TYPE_TEXT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        who = self.user.username if self.user_id else 'system'
        return f'{who} on post {self.post_id}'


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

