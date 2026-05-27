from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q

from apps.core.models import (
    DirectConversation,
    EventChatMessage,
    Post,
    PostInterest,
)

User = get_user_model()


def normalize_dm_users(user1, user2):
    if user1.pk < user2.pk:
        return user1, user2
    return user2, user1


def get_or_create_dm(post, user1, user2):
    if user1.pk == user2.pk:
        raise ValueError('Cannot create a conversation with yourself.')
    user_a, user_b = normalize_dm_users(user1, user2)
    return DirectConversation.objects.get_or_create(
        post=post, user_a=user_a, user_b=user_b,
    )


def ensure_dm_with_host(post, guest):
    """Create guest ↔ host thread when someone marks interested."""
    if not post.author_id or guest.pk == post.author_id:
        return None
    conv, _ = get_or_create_dm(post, guest, post.author)
    return conv


def user_can_access_dm(conversation, user):
    if not user.is_authenticated:
        return False
    return user.pk in (conversation.user_a_id, conversation.user_b_id)


def conversation_other_user(conversation, user):
    if user.pk == conversation.user_a_id:
        return conversation.user_b
    return conversation.user_a


def user_dm_threads(user):
    return (
        DirectConversation.objects.filter(Q(user_a=user) | Q(user_b=user))
        .select_related(
            'post', 'post__venue', 'post__time', 'post__author',
            'user_a', 'user_b', 'user_a__profile', 'user_b__profile',
        )
        .annotate(last_message_at=Max('messages__created_at'))
        .order_by('-last_message_at', '-updated_at')
    )


def get_thread_meta(conversation, user):
    post = conversation.post
    other = conversation_other_user(conversation, user)
    is_host = post.author_id == user.pk
    interest = None
    if not is_host:
        interest = PostInterest.objects.filter(post=post, user=user).first()

    event_title = (post.message[:80] + '…') if len(post.message) > 80 else post.message

    return {
        'conversation_id': conversation.id,
        'post_id': post.id,
        'post_slug': post.slug,
        'other_user_id': other.pk,
        'other_user_name': other.get_full_name() or other.username,
        'other_username': other.username,
        'other_avatar': _avatar_url(other),
        'title': other.get_full_name() or other.username,
        'subtitle': event_title,
        'venue': str(post.venue) if post.venue else '',
        'date': post.date.strftime('%d %b %Y') if post.date else '',
        'time': str(post.time) if post.time else '',
        'event_status': post.event_status,
        'is_locked': post.event_status == Post.STATUS_CONFIRMED,
        'is_host': is_host,
        'my_participation': interest.participation_status if interest else (
            PostInterest.STATUS_CONFIRMED if is_host else None
        ),
        'interested_count': post.interests.count(),
        'confirmed_count': post.interests.filter(
            participation_status=PostInterest.STATUS_CONFIRMED,
        ).count(),
    }


def _avatar_url(user):
    try:
        if hasattr(user, 'profile') and user.profile.profile_image:
            return user.profile.profile_image.url
    except Exception:
        pass
    return ''


def serialize_chat_message(msg, current_user_id=None):
    """Serialize for API or WebSocket. Pass current_user_id for HTTP responses only."""
    is_system = msg.message_type in (
        EventChatMessage.TYPE_SYSTEM,
        EventChatMessage.TYPE_ATTENDANCE,
        EventChatMessage.TYPE_EVENT_CONFIRMED,
    )
    data = {
        'id': msg.id,
        'body': msg.body,
        'message_type': msg.message_type,
        'is_system': is_system,
        'sender_id': msg.user_id,
        'user': None,
        'username': '',
        'avatar': '',
        'is_mine': False,
        'created_at': msg.created_at.strftime('%I:%M %p'),
        'created_at_full': msg.created_at.isoformat(),
    }
    if msg.user_id:
        data['user'] = msg.user.get_full_name() or msg.user.username
        data['username'] = msg.user.username
        data['avatar'] = _avatar_url(msg.user)
        if current_user_id is not None:
            data['is_mine'] = msg.user_id == current_user_id
    return data


def create_system_message(conversation, body):
    return EventChatMessage.objects.create(
        conversation=conversation,
        post=conversation.post,
        user=None,
        body=body,
        message_type=EventChatMessage.TYPE_SYSTEM,
    )


def create_attendance_message(conversation, user, confirmed=True):
    name = user.get_full_name() or user.username
    body = f'{name} confirmed they are coming to this match.' if confirmed else (
        f'{name} cannot make it to this match.'
    )
    return EventChatMessage.objects.create(
        conversation=conversation,
        post=conversation.post,
        user=user,
        body=body,
        message_type=EventChatMessage.TYPE_ATTENDANCE,
    )


def create_event_confirmed_message(conversation, user, body):
    return EventChatMessage.objects.create(
        conversation=conversation,
        post=conversation.post,
        user=user,
        body=body,
        message_type=EventChatMessage.TYPE_EVENT_CONFIRMED,
    )
