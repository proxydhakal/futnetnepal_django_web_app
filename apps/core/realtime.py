import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.core.models import Notification


def serialize_notification(n):
    actor = n.actor
    return {
        'id': n.id,
        'type': n.notification_type,
        'message': n.message,
        'url': n.url,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%b %d, %I:%M %p'),
        'actor': actor.get_full_name() or actor.username if actor else 'System',
        'post_id': n.post_id,
    }


def unread_count_for(user_id):
    return Notification.objects.filter(recipient_id=user_id, is_read=False).count()


def broadcast_to_user(user_id, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f'user_notifications_{user_id}',
        {'type': 'push.message', 'payload': payload},
    )


def push_notification_created(notification):
    payload = {
        'event': 'notification',
        'notification': serialize_notification(notification),
        'unread_count': unread_count_for(notification.recipient_id),
    }
    broadcast_to_user(notification.recipient_id, payload)


def push_unread_count(user_id):
    broadcast_to_user(user_id, {
        'event': 'unread_count',
        'unread_count': unread_count_for(user_id),
    })


def broadcast_dm_message(conversation_id, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f'dm_{conversation_id}',
        {'type': 'push.message', 'payload': payload},
    )
