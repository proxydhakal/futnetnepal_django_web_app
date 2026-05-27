from django.db.models import BooleanField, Case, Count, Exists, OuterRef, Q, Value, When

from apps.core.models import Post, PostComment, PostInterest, PostReaction


def posts_with_engagement(user):
    user_interest = PostInterest.objects.filter(post=OuterRef('pk'), user=user)
    user_like = PostReaction.objects.filter(
        post=OuterRef('pk'), user=user, reaction_type=PostReaction.REACTION_LIKE,
    )
    return (
        Post.objects.select_related('author__profile', 'venue', 'location', 'time')
        .annotate(
            interest_count=Count('interests', distinct=True),
            like_count=Count(
                'reactions',
                filter=Q(reactions__reaction_type=PostReaction.REACTION_LIKE),
                distinct=True,
            ),
            comment_count=Count('comments', distinct=True),
            user_interested=Exists(user_interest),
            user_liked=Exists(user_like),
            user_can_chat=Case(
                When(author=user, then=Value(True)),
                default=Exists(user_interest),
                output_field=BooleanField(),
            ),
        )
        .order_by('-created_at')
    )


def build_comment_tree(post_id):
    comments = (
        PostComment.objects.filter(post_id=post_id, parent__isnull=True)
        .select_related('user')
        .prefetch_related('replies__user')
    )
    return [_serialize_comment(c) for c in comments]


def _serialize_comment(comment):
    return {
        'id': comment.id,
        'body': comment.body,
        'user': comment.user.get_full_name() or comment.user.username,
        'username': comment.user.username,
        'created_at': comment.created_at.strftime('%b %d, %Y %I:%M %p'),
        'replies': [_serialize_comment(r) for r in comment.replies.select_related('user').all()],
    }
