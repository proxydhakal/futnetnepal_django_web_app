"""Shared match engagement logic for web JSON views and REST API."""

from apps.core.chat import ensure_dm_with_host
from apps.core.engagement import build_comment_tree
from apps.core.event_guard import is_event_locked
from apps.core.models import Post, PostComment, PostInterest, PostReaction
from apps.core.notifications import notify_comment, notify_interest, notify_like


class EngagementError(Exception):
    def __init__(self, message, status_code=400, locked=False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.locked = locked


def toggle_post_interest(post, user):
    if is_event_locked(post):
        raise EngagementError(
            'This match is confirmed. Chat and interest changes are closed.',
            status_code=403,
            locked=True,
        )
    interest, created = PostInterest.objects.get_or_create(post=post, user=user)
    if not created:
        interest.delete()
        interested = False
    else:
        interested = True
        notify_interest(post, user, True)
        ensure_dm_with_host(post, user)
    return {
        'interested': interested,
        'interest_count': post.interests.count(),
    }


def toggle_post_reaction(post, user, reaction_type=PostReaction.REACTION_LIKE):
    if is_event_locked(post):
        raise EngagementError(
            'Likes and comments are closed — this match is confirmed.',
            status_code=403,
            locked=True,
        )
    reaction, created = PostReaction.objects.get_or_create(
        post=post, user=user, reaction_type=reaction_type,
    )
    if not created:
        reaction.delete()
        liked = False
    else:
        liked = True
        notify_like(post, user, True)
    return {
        'liked': liked,
        'like_count': post.reactions.filter(reaction_type=reaction_type).count(),
    }


def add_post_comment(post, user, body, parent_id=None):
    if is_event_locked(post):
        raise EngagementError(
            'Likes and comments are closed — this match is confirmed.',
            status_code=403,
            locked=True,
        )
    body = (body or '').strip()
    if not body:
        raise EngagementError('Comment cannot be empty.', status_code=400)
    parent = None
    if parent_id:
        parent = PostComment.objects.filter(pk=parent_id, post=post).first()
        if parent is None:
            raise EngagementError('Invalid parent comment.', status_code=400)
    PostComment.objects.create(post=post, user=user, parent=parent, body=body)
    notify_comment(post, user, parent)
    return {
        'comment_count': post.comments.count(),
        'comments': build_comment_tree(post.pk),
    }
