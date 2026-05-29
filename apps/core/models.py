import math

from django.conf import settings
from django.db import models
from django.utils import timezone

from ckeditor_uploader.fields import RichTextUploadingField

from apps.core.slugs import make_slug
from futnetnepal.models import TimestampedSoftDeleteModel
from futnetnepal.uuids import time_ordered_uuid


class Location(TimestampedSoftDeleteModel):
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'locations'

    def __str__(self):
        return self.name


class Venue(TimestampedSoftDeleteModel):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    picture = models.ImageField(upload_to='media/venue', null=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=255, null=True)
    phone = models.IntegerField(null=True)
    email = models.EmailField(null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.name, Venue, instance_pk=self.pk, max_length=60)
        super().save(*args, **kwargs)


class Time(TimestampedSoftDeleteModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.name, Time, instance_pk=self.pk, max_length=80)
        super().save(*args, **kwargs)


class Post(TimestampedSoftDeleteModel):
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

    id = models.UUIDField(primary_key=True, default=time_ordered_uuid, editable=False)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    event_status = models.CharField(
        max_length=20, choices=EVENT_STATUS_CHOICES, default=STATUS_OPEN,
    )
    date = models.DateField()
    time = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    message = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = (self.message or 'event')[:50]
            self.slug = make_slug(base, Post, instance_pk=self.pk, max_length=80)
        super().save(*args, **kwargs)

    def whenpublished(self):
        now = timezone.now()
        diff = now - self.created_at

        if diff.days == 0 and diff.seconds >= 0 and diff.seconds < 60:
            seconds = diff.seconds
            if seconds == 1:
                return str(seconds) + ' second ago'
            return str(seconds) + ' seconds ago'

        if diff.days == 0 and diff.seconds >= 60 and diff.seconds < 3600:
            minutes = math.floor(diff.seconds / 60)
            if minutes == 1:
                return str(minutes) + ' minute ago'
            return str(minutes) + ' minutes ago'

        if diff.days == 0 and diff.seconds >= 3600 and diff.seconds < 86400:
            hours = math.floor(diff.seconds / 3600)
            if hours == 1:
                return str(hours) + ' hour ago'
            return str(hours) + ' hours ago'

        if diff.days >= 1 and diff.days < 30:
            days = diff.days
            if days == 1:
                return str(days) + ' day ago'
            return str(days) + ' days ago'

        if diff.days >= 30 and diff.days < 365:
            months = math.floor(diff.days / 30)
            if months == 1:
                return str(months) + ' month ago'
            return str(months) + ' months ago'

        if diff.days >= 365:
            years = math.floor(diff.days / 365)
            if years == 1:
                return str(years) + ' year ago'
            return str(years) + ' years ago'


class VenueBooking(TimestampedSoftDeleteModel):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='venue_bookings')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    time_slot = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

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


class PostInterest(TimestampedSoftDeleteModel):
    STATUS_INTERESTED = 'interested'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_DECLINED = 'declined'
    PARTICIPATION_CHOICES = [
        (STATUS_INTERESTED, 'Interested'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_DECLINED, 'Declined'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='interests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_interests')
    participation_status = models.CharField(
        max_length=20, choices=PARTICIPATION_CHOICES, default=STATUS_INTERESTED,
    )

    class Meta:
        unique_together = [['post', 'user']]


class PostReaction(TimestampedSoftDeleteModel):
    REACTION_LIKE = 'like'
    REACTION_CHOICES = [(REACTION_LIKE, 'Like')]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES, default=REACTION_LIKE)

    class Meta:
        unique_together = [['post', 'user', 'reaction_type']]


class PostComment(TimestampedSoftDeleteModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_comments')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies',
    )
    body = models.TextField()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.user.username} on post {self.post_id}'


class Notification(TimestampedSoftDeleteModel):
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications_sent',
        null=True, blank=True,
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True,
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username}: {self.message[:40]}'


class DirectConversation(TimestampedSoftDeleteModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='direct_conversations')
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dm_conversations_as_a',
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dm_conversations_as_b',
    )

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


class EventChatMessage(TimestampedSoftDeleteModel):
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_chat_messages',
        null=True, blank=True,
    )
    body = models.TextField(max_length=1000)
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPE_CHOICES, default=TYPE_TEXT,
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        who = self.user.username if self.user_id else 'system'
        return f'{who} on post {self.post_id}'


class Contact(TimestampedSoftDeleteModel):
    SUBJECT_FUTSAL_BOOKING = 'futsal_booking'
    SUBJECT_OPPONENT_FINDER = 'opponent_finder'
    SUBJECT_GENERAL_INQUIRY = 'general_inquiry'
    SUBJECT_OTHER = 'other'
    SUBJECT_CHOICES = [
        (SUBJECT_FUTSAL_BOOKING, 'Futsal Booking'),
        (SUBJECT_OPPONENT_FINDER, 'Opponent Finder'),
        (SUBJECT_GENERAL_INQUIRY, 'General Inquiry'),
        (SUBJECT_OTHER, 'Other'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_RESPONDED = 'responded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RESPONDED, 'Responded'),
    ]

    fullname = models.CharField(max_length=255)
    phone = models.BigIntegerField()
    email = models.EmailField()
    subject = models.CharField(
        max_length=32,
        choices=SUBJECT_CHOICES,
        default=SUBJECT_GENERAL_INQUIRY,
        db_index=True,
    )
    message = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    admin_response = models.TextField(blank=True, default='')
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_inquiry_replies',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.fullname


class NewsletterSubscription(TimestampedSoftDeleteModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'newsletter subscription'
        verbose_name_plural = 'newsletter subscriptions'

    def __str__(self):
        return f'{self.name} <{self.email}>'


class UserReview(TimestampedSoftDeleteModel):
    RATING_MIN = 1
    RATING_MAX = 5

    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    rating = models.PositiveSmallIntegerField()
    message = models.TextField()
    is_approved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'user review'
        verbose_name_plural = 'user reviews'

    def __str__(self):
        return f'{self.name} ({self.rating}/5)'


class SiteConfiguration(models.Model):
    """Singleton site-wide branding, SEO, and page section content."""

    site_title = models.CharField(max_length=120, default='Futnet Nepal')
    logo = models.ImageField(upload_to='site/branding', blank=True, null=True)
    favicon = models.FileField(upload_to='site/branding', blank=True, null=True)

    meta_description = models.TextField(
        blank=True,
        max_length=320,
        help_text='Default SEO description for public pages.',
    )
    meta_keywords = models.CharField(
        blank=True,
        max_length=255,
        help_text='Comma-separated default keywords.',
    )

    about_hero_eyebrow = models.CharField(max_length=120, blank=True, default='Our story')
    about_hero_title = models.CharField(max_length=200, blank=True, default='About Us')
    about_hero_subtitle = models.CharField(max_length=500, blank=True, default='')
    about_content = RichTextUploadingField(blank=True)
    about_image = models.ImageField(upload_to='site/about', blank=True, null=True)
    about_youtube_url = models.URLField(blank=True, max_length=500)
    about_cta_label = models.CharField(max_length=80, blank=True, default='Join the community')

    partner_hero_eyebrow = models.CharField(max_length=120, blank=True, default='Collaborate')
    partner_hero_title = models.CharField(max_length=200, blank=True, default='Partner With Us')
    partner_hero_subtitle = models.CharField(max_length=500, blank=True, default='')
    partner_content = RichTextUploadingField(blank=True)
    partner_bullets = models.TextField(
        blank=True,
        help_text='One partnership benefit per line (shown as a checklist).',
    )
    partner_image = models.ImageField(upload_to='site/partner', blank=True, null=True)

    home_welcome_eyebrow = models.CharField(max_length=120, blank=True, default='Welcome to')
    home_welcome_title = models.CharField(max_length=200, blank=True, default='Futnet Nepal')
    home_welcome_content = RichTextUploadingField(blank=True)
    home_youtube_url = models.URLField(blank=True, max_length=500)

    company_name = models.CharField(max_length=200, blank=True, default='Futnet Nepal Pvt. Ltd.')
    contact_address = models.TextField(blank=True, default='Balaju-16, Kathmandu, Nepal')
    contact_email = models.EmailField(blank=True, default='info@futnetnepal.com')
    contact_phone = models.CharField(max_length=40, blank=True, default='+977 9840177381')
    contact_website = models.URLField(blank=True, max_length=500)

    facebook_url = models.URLField(blank=True, max_length=500)
    twitter_url = models.URLField(blank=True, max_length=500)
    instagram_url = models.URLField(blank=True, max_length=500)
    youtube_social_url = models.URLField(blank=True, max_length=500)
    linkedin_url = models.URLField(blank=True, max_length=500)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'site configuration'
        verbose_name_plural = 'site configuration'

    def __str__(self):
        return self.site_title or 'Site configuration'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CMSPage(TimestampedSoftDeleteModel):
    """Dynamic content pages (e.g. booking policy) with optional nav/footer links."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    hero_image = models.ImageField(upload_to='site/pages/heroes', blank=True, null=True)
    content = RichTextUploadingField()
    meta_description = models.TextField(blank=True, max_length=320)
    meta_keywords = models.CharField(blank=True, max_length=255)
    is_published = models.BooleanField(default=True, db_index=True)
    show_in_navbar = models.BooleanField(default=False, db_index=True)
    show_in_footer = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['sort_order', 'title']
        verbose_name = 'CMS page'
        verbose_name_plural = 'CMS pages'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.title, CMSPage, instance_pk=self.pk, max_length=220)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('cms_page', kwargs={'slug': self.slug})
