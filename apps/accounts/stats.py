from django.db.models import Q

from apps.core.models import (
    DirectConversation,
    Post,
    PostComment,
    PostInterest,
    PostReaction,
    VenueBooking,
)


def user_profile_stats(user):
    """Aggregate engagement and activity counts for the profile stats section."""
    user_posts = Post.objects.filter(author=user)
    return {
        'matches_hosted': user_posts.count(),
        'matches_confirmed': user_posts.filter(event_status=Post.STATUS_CONFIRMED).count(),
        'matches_open': user_posts.filter(
            event_status__in=(Post.STATUS_OPEN, Post.STATUS_DISCUSSING),
        ).count(),
        'interest_shown': PostInterest.objects.filter(user=user).count(),
        'likes_given': PostReaction.objects.filter(user=user).count(),
        'comments_made': PostComment.objects.filter(user=user).count(),
        'likes_received': PostReaction.objects.filter(post__author=user).count(),
        'interest_received': PostInterest.objects.filter(post__author=user).exclude(user=user).count(),
        'venue_bookings': VenueBooking.objects.filter(user=user).count(),
        'conversations': DirectConversation.objects.filter(
            Q(user_a=user) | Q(user_b=user),
        ).count(),
    }
