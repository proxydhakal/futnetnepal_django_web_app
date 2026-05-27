from django.http import JsonResponse

from apps.core.models import Post


def is_event_locked(post):
    return post.event_status == Post.STATUS_CONFIRMED


def event_locked_response():
    return JsonResponse(
        {
            'success': False,
            'error': 'This match is confirmed. Chat and interest changes are closed.',
            'locked': True,
        },
        status=403,
    )


def social_engagement_denied_response():
    return JsonResponse(
        {
            'success': False,
            'error': 'Likes and comments are closed — this match is confirmed.',
            'locked': True,
        },
        status=403,
    )
