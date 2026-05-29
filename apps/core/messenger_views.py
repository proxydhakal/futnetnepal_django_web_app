from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from apps.core.chat import (
    conversation_other_user,
    create_attendance_message,
    create_event_confirmed_message,
    create_system_message,
    get_or_create_dm,
    get_thread_meta,
    serialize_chat_message,
    user_can_access_dm,
    user_dm_threads,
)
from apps.core.event_guard import event_locked_response, is_event_locked
from apps.core.models import DirectConversation, EventChatMessage, Post, PostInterest
from apps.core.notifications import notify_dm
from apps.core.realtime import broadcast_dm_message

User = get_user_model()


def _dm_url(conversation_id):
    return f'/messages/c/{conversation_id}/'


@login_required
def messages_inbox_data(request):
    threads = []
    for conv in user_dm_threads(request.user):
        meta = get_thread_meta(conv, request.user)
        last = conv.messages.order_by('-created_at').first()
        threads.append({
            **meta,
            'last_message': last.body[:60] if last else 'No messages yet',
            'last_message_at': last.created_at.strftime('%b %d, %I:%M %p') if last else '',
            'url': _dm_url(conv.id),
        })
    return JsonResponse({'success': True, 'threads': threads})


class MessagesView(LoginRequiredMixin, View):
    template_name = 'core/messages.html'

    def get(self, request, conversation_id=None, post_slug=None, username=None):
        active_conversation = None
        if conversation_id:
            active_conversation = get_object_or_404(
                DirectConversation.objects.select_related('post', 'user_a', 'user_b'),
                pk=conversation_id,
            )
            if not user_can_access_dm(active_conversation, request.user):
                active_conversation = None
        elif post_slug and username:
            post = get_object_or_404(Post, slug=post_slug)
            peer = get_object_or_404(User, username=username)
            if request.user.pk not in (post.author_id, peer.pk):
                return redirect('messages')
            if request.user.pk == peer.pk:
                return redirect('messages')
            conv, _ = get_or_create_dm(post, request.user, peer)
            return redirect('messages_conversation', conversation_id=conv.id)
        elif post_slug:
            post = get_object_or_404(Post, slug=post_slug)
            peer = post.author
            if not peer or peer.pk == request.user.pk:
                return redirect('messages')
            conv, _ = get_or_create_dm(post, request.user, peer)
            return redirect('messages_conversation', conversation_id=conv.id)

        return render(request, self.template_name, {
            'active_conversation': active_conversation,
        })


@login_required
@require_GET
def dm_chat_thread(request, conversation_id):
    conv = get_object_or_404(
        DirectConversation.objects.select_related('post', 'user_a', 'user_b'),
        pk=conversation_id,
    )
    if not user_can_access_dm(conv, request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    after_id = int(request.GET.get('after_id', 0) or 0)
    qs = EventChatMessage.objects.filter(conversation=conv).select_related('user')
    if after_id:
        messages = list(qs.filter(id__gt=after_id))
    else:
        messages = list(reversed(list(qs.order_by('-created_at')[:80])))

    return JsonResponse({
        'success': True,
        'thread': get_thread_meta(conv, request.user),
        'messages': [
            serialize_chat_message(m, request.user.pk) for m in messages
        ],
    })


def _send_dm_and_broadcast(conversation, user, body, message_type=EventChatMessage.TYPE_TEXT):
    post = conversation.post
    if is_event_locked(post) and message_type == EventChatMessage.TYPE_TEXT:
        raise ValueError('locked')
    if post.event_status == Post.STATUS_OPEN:
        post.event_status = Post.STATUS_DISCUSSING
        post.save(update_fields=['event_status'])
    msg = EventChatMessage.objects.create(
        conversation=conversation,
        post=post,
        user=user,
        body=body[:1000],
        message_type=message_type,
    )
    conversation.save(update_fields=['updated_at'])
    if message_type == EventChatMessage.TYPE_TEXT:
        notify_dm(conversation, user, body)
    payload = {
        'event': 'chat_message',
        'message': serialize_chat_message(msg),
        'thread': get_thread_meta(conversation, user),
    }
    broadcast_dm_message(conversation.id, payload)
    return serialize_chat_message(msg, user.pk)


@login_required
@require_POST
def dm_chat_send(request, conversation_id):
    conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=conversation_id)
    if not user_can_access_dm(conv, request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    if is_event_locked(conv.post):
        return event_locked_response()
    from django.core.exceptions import ValidationError as DjangoValidationError
    from futnetnepal.input_validation import sanitize_plain_text

    try:
        body = sanitize_plain_text(
            request.POST.get('body') or '',
            max_length=1000,
            multiline=True,
            min_length=1,
            field_label='Message',
        )
    except DjangoValidationError as exc:
        return JsonResponse({'success': False, 'error': exc.messages[0]}, status=400)
    data = _send_dm_and_broadcast(conv, request.user, body)
    data['is_mine'] = True
    return JsonResponse({
        'success': True,
        'message': data,
        'thread': get_thread_meta(conv, request.user),
    })


@login_required
@require_POST
def event_confirm_attendance(request, conversation_id):
    conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=conversation_id)
    if not user_can_access_dm(conv, request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    post = conv.post
    if is_event_locked(post):
        return event_locked_response()
    if post.author_id == request.user.pk:
        return JsonResponse({'success': False, 'error': 'Host is already on the roster.'}, status=400)
    interest, _ = PostInterest.objects.get_or_create(post=post, user=request.user)
    interest.participation_status = PostInterest.STATUS_CONFIRMED
    interest.save(update_fields=['participation_status'])
    msg = create_attendance_message(conv, request.user, confirmed=True)
    data = serialize_chat_message(msg, request.user.pk)
    broadcast_dm_message(conv.id, {
        'event': 'chat_message',
        'message': serialize_chat_message(msg),
        'thread': get_thread_meta(conv, request.user),
    })
    return JsonResponse({
        'success': True,
        'thread': get_thread_meta(conv, request.user),
        'message': data,
    })


@login_required
@require_POST
def event_decline_attendance(request, conversation_id):
    conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=conversation_id)
    if not user_can_access_dm(conv, request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    post = conv.post
    if is_event_locked(post):
        return event_locked_response()
    if post.author_id == request.user.pk:
        return JsonResponse({'success': False, 'error': 'Host cannot decline.'}, status=400)
    interest = get_object_or_404(PostInterest, post=post, user=request.user)
    interest.participation_status = PostInterest.STATUS_DECLINED
    interest.save(update_fields=['participation_status'])
    msg = create_attendance_message(conv, request.user, confirmed=False)
    data = serialize_chat_message(msg, request.user.pk)
    broadcast_dm_message(conv.id, {
        'event': 'chat_message',
        'message': serialize_chat_message(msg),
        'thread': get_thread_meta(conv, request.user),
    })
    return JsonResponse({'success': True, 'thread': get_thread_meta(conv, request.user), 'message': data})


def confirm_post_match(post, host_user, primary_conv=None):
    """Host confirms match — lock event and notify all interested players."""
    if post.author_id != host_user.pk:
        raise PermissionError('Only the host can confirm the match.')
    if post.event_status == Post.STATUS_CONFIRMED:
        return None
    post.event_status = Post.STATUS_CONFIRMED
    post.save(update_fields=['event_status'])
    name = host_user.get_full_name() or host_user.username
    body = f'{name} confirmed this match is ON. See you on the pitch!'
    from apps.core.notifications import notify

    if primary_conv is None and post.interests.exists():
        first = post.interests.select_related('user').first()
        if first:
            primary_conv, _ = get_or_create_dm(post, host_user, first.user)

    if primary_conv:
        msg = create_event_confirmed_message(primary_conv, host_user, body)
        broadcast_dm_message(primary_conv.id, {
            'event': 'chat_message',
            'message': serialize_chat_message(msg),
            'thread': get_thread_meta(primary_conv, host_user),
        })

    notified_ids = set()
    for pi in PostInterest.objects.filter(post=post).exclude(
        participation_status=PostInterest.STATUS_DECLINED,
    ).select_related('user'):
        if pi.user_id == host_user.pk or pi.user_id in notified_ids:
            continue
        peer_conv, _ = get_or_create_dm(post, host_user, pi.user)
        if not primary_conv or peer_conv.pk != primary_conv.pk:
            peer_msg = create_event_confirmed_message(peer_conv, host_user, body)
            broadcast_dm_message(peer_conv.id, {
                'event': 'chat_message',
                'message': serialize_chat_message(peer_msg),
                'thread': get_thread_meta(peer_conv, host_user),
            })
        notify(
            pi.user, host_user, 'chat',
            f'{name} confirmed the match — you\'re all set!',
            _dm_url(peer_conv.id),
            post,
        )
        notified_ids.add(pi.user_id)
    return primary_conv


@login_required
@require_POST
def event_confirm_match(request, conversation_id):
    conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=conversation_id)
    if not user_can_access_dm(conv, request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    try:
        confirm_post_match(conv.post, request.user, primary_conv=conv)
    except PermissionError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    return JsonResponse({
        'success': True,
        'event_status': conv.post.event_status,
        'thread': get_thread_meta(conv, request.user),
    })


def _reopen_confirmed_event(post, actor):
    """Host cancels match confirmation — unlock comments, reactions, and chat."""
    post.event_status = Post.STATUS_DISCUSSING
    post.save(update_fields=['event_status'])
    name = actor.get_full_name() or actor.username
    body = f'{name} cancelled match confirmation. Discussion, chat, and reactions are open again.'
    for conv in DirectConversation.objects.filter(post=post):
        msg = create_system_message(conv, body)
        payload = {
            'event': 'chat_message',
            'message': serialize_chat_message(msg),
            'thread': get_thread_meta(conv, actor),
        }
        broadcast_dm_message(conv.id, payload)


@login_required
@require_POST
def event_cancel_confirmation(request, conversation_id):
    conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=conversation_id)
    if not user_can_access_dm(conv, request.user):
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)
    post = conv.post
    if post.author_id != request.user.pk:
        return JsonResponse({'success': False, 'error': 'Only the host can cancel confirmation.'}, status=403)
    if post.event_status != Post.STATUS_CONFIRMED:
        return JsonResponse({'success': False, 'error': 'This event is not confirmed.'}, status=400)
    _reopen_confirmed_event(post, request.user)
    return JsonResponse({
        'success': True,
        'thread': get_thread_meta(conv, request.user),
        'event_status': post.event_status,
    })
