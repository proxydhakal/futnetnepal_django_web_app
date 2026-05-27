from apps.core.models import Notification, Post, PostInterest
from apps.core.realtime import push_notification_created


def _actor_name(user):
    if not user:
        return 'Someone'
    return user.get_full_name() or user.username


def notify(recipient, actor, notification_type, message, url='', post=None):
    if not recipient or not actor or recipient.pk == actor.pk:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        post=post,
        notification_type=notification_type,
        message=message,
        url=url or (f'/home/' if post else ''),
    )
    push_notification_created(notification)
    return notification


def notify_post_author(post, actor, notification_type, message, url=''):
    if not post.author_id:
        return None
    return notify(post.author, actor, notification_type, message, url, post)


def notify_interest(post, actor, interested):
    if not interested:
        return None
    name = _actor_name(actor)
    return notify_post_author(
        post, actor, Notification.TYPE_INTEREST,
        f'{name} is interested in your hosted event',
    )


def notify_like(post, actor, liked):
    if not liked:
        return None
    name = _actor_name(actor)
    return notify_post_author(
        post, actor, Notification.TYPE_LIKE,
        f'{name} liked your hosted event',
    )


def notify_comment(post, actor, parent_comment=None):
    name = _actor_name(actor)
    url = ''
    if parent_comment and parent_comment.user_id != post.author_id:
        notify(
            parent_comment.user, actor, Notification.TYPE_REPLY,
            f'{name} replied to your comment', url, post,
        )
    if parent_comment:
        msg = f'{name} replied on your event'
        ntype = Notification.TYPE_REPLY
    else:
        msg = f'{name} commented on your hosted event'
        ntype = Notification.TYPE_COMMENT
    return notify_post_author(post, actor, ntype, msg, url)


def notify_dm(conversation, actor, message_preview=''):
    """Notify only the other person in a private conversation."""
    from apps.core.chat import conversation_other_user

    recipient = conversation_other_user(conversation, actor)
    name = _actor_name(actor)
    preview = (message_preview[:40] + '…') if len(message_preview) > 40 else message_preview
    msg = f'{name}: {preview}' if preview else f'{name} sent you a message'
    url = f'/messages/c/{conversation.id}/'
    n = notify(recipient, actor, Notification.TYPE_CHAT, msg, url, conversation.post)
    return [n] if n else []


def user_can_access_event_chat(post, user):
    """May start or view DMs about this event."""
    if not user.is_authenticated:
        return False
    if post.author_id == user.pk:
        return True
    return PostInterest.objects.filter(post=post, user=user).exists()
