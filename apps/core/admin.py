from django.contrib import admin
from apps.core.models import (
    Location, Venue, Time, Post, Contact,
    VenueBooking, PostInterest, PostReaction, PostComment,
    Notification, EventChatMessage, DirectConversation,
)

admin.site.register(Location)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'location')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')


@admin.register(Time)
class TimeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('slug', 'author', 'venue', 'date', 'event_status', 'created_at')
    list_filter = ('event_status',)
    prepopulated_fields = {'slug': ('message',)}
    search_fields = ('slug', 'message', 'author__username')
admin.site.register(Contact)


@admin.register(VenueBooking)
class VenueBookingAdmin(admin.ModelAdmin):
    list_display = ('venue', 'user', 'booking_date', 'preferred_time', 'time_slot', 'status', 'created_at')
    list_filter = ('status', 'booking_date')
    search_fields = ('venue__name', 'user__username')


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'parent', 'created_at')
    search_fields = ('body', 'user__username')


@admin.register(PostInterest)
class PostInterestAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'participation_status', 'created_at')
    list_filter = ('participation_status',)


admin.site.register(PostReaction)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')


@admin.register(DirectConversation)
class DirectConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user_a', 'user_b', 'updated_at')
    search_fields = ('user_a__username', 'user_b__username', 'post__slug')


@admin.register(EventChatMessage)
class EventChatMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'post', 'user', 'message_type', 'created_at')
    list_filter = ('message_type',)
    search_fields = ('body', 'user__username')