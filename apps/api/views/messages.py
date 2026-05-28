from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import IsEmailVerified
from apps.api.serializers import ChatSendSerializer, OpenConversationSerializer, UserBriefSerializer
from apps.core.chat import (
    get_or_create_dm,
    get_thread_meta,
    serialize_chat_message,
    user_can_access_dm,
    user_dm_threads,
)
from apps.core.event_guard import event_locked_response, is_event_locked
from apps.core.models import DirectConversation, EventChatMessage, Post, PostInterest
from apps.core.messenger_views import (
    _reopen_confirmed_event,
    _send_dm_and_broadcast,
    confirm_post_match,
    create_attendance_message,
)

User = get_user_model()


class ConversationViewSet(viewsets.ViewSet):
    permission_classes = [IsEmailVerified]

    def list(self, request):
        threads = []
        for conv in user_dm_threads(request.user):
            meta = get_thread_meta(conv, request.user)
            last = conv.messages.order_by('-created_at').first()
            other_user = conv.user_b if conv.user_a_id == request.user.pk else conv.user_a
            threads.append({
                **meta,
                'other_user': UserBriefSerializer(other_user, context={'request': request}).data,
                'last_message': last.body[:120] if last else '',
                'last_message_at': last.created_at.isoformat() if last else '',
            })
        return Response({'success': True, 'threads': threads})

    def retrieve(self, request, pk=None):
        conv = get_object_or_404(
            DirectConversation.objects.select_related('post', 'user_a', 'user_b'),
            pk=pk,
        )
        if not user_can_access_dm(conv, request.user):
            return Response({'success': False, 'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        after_id = int(request.query_params.get('after_id', 0) or 0)
        qs = EventChatMessage.objects.filter(conversation=conv).select_related('user')
        if after_id:
            messages = list(qs.filter(id__gt=after_id))
        else:
            messages = list(reversed(list(qs.order_by('-created_at')[:80])))
        return Response({
            'success': True,
            'thread': get_thread_meta(conv, request.user),
            'messages': [serialize_chat_message(m, request.user.pk) for m in messages],
        })

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        conv = get_object_or_404(
            DirectConversation.objects.select_related('post'), pk=pk,
        )
        if not user_can_access_dm(conv, request.user):
            return Response({'success': False, 'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        if is_event_locked(conv.post):
            return Response(
                {'success': False, 'error': 'This match is confirmed. Chat is closed.', 'locked': True},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = ChatSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = _send_dm_and_broadcast(conv, request.user, ser.validated_data['body'])
        except ValueError:
            return Response(
                {'success': False, 'error': 'Chat is closed for this match.', 'locked': True},
                status=status.HTTP_403_FORBIDDEN,
            )
        data['is_mine'] = True
        return Response({
            'success': True,
            'message': data,
            'thread': get_thread_meta(conv, request.user),
        })

    @action(detail=True, methods=['post'], url_path='confirm-attendance')
    def confirm_attendance(self, request, pk=None):
        from apps.core.realtime import broadcast_dm_message

        conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=pk)
        if not user_can_access_dm(conv, request.user):
            return Response({'success': False, 'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        if is_event_locked(conv.post):
            return Response(
                {'success': False, 'error': 'This match is confirmed.', 'locked': True},
                status=status.HTTP_403_FORBIDDEN,
            )
        post = conv.post
        if post.author_id == request.user.pk:
            return Response(
                {'success': False, 'error': 'Host is already on the roster.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        return Response({
            'success': True,
            'thread': get_thread_meta(conv, request.user),
            'message': data,
        })

    @action(detail=True, methods=['post'], url_path='decline-attendance')
    def decline_attendance(self, request, pk=None):
        from apps.core.realtime import broadcast_dm_message

        conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=pk)
        if not user_can_access_dm(conv, request.user):
            return Response({'success': False, 'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        if is_event_locked(conv.post):
            return Response(
                {'success': False, 'error': 'This match is confirmed.', 'locked': True},
                status=status.HTTP_403_FORBIDDEN,
            )
        post = conv.post
        if post.author_id == request.user.pk:
            return Response({'success': False, 'error': 'Host cannot decline.'}, status=status.HTTP_400_BAD_REQUEST)
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
        return Response({'success': True, 'thread': get_thread_meta(conv, request.user), 'message': data})

    @action(detail=True, methods=['post'], url_path='confirm-match')
    def confirm_match(self, request, pk=None):
        conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=pk)
        if not user_can_access_dm(conv, request.user):
            return Response({'success': False, 'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            confirm_post_match(conv.post, request.user, primary_conv=conv)
        except PermissionError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        conv.post.refresh_from_db()
        return Response({
            'success': True,
            'event_status': conv.post.event_status,
            'thread': get_thread_meta(conv, request.user),
        })

    @action(detail=True, methods=['post'], url_path='cancel-confirmation')
    def cancel_confirmation(self, request, pk=None):
        conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=pk)
        if not user_can_access_dm(conv, request.user):
            return Response({'success': False, 'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        post = conv.post
        if post.author_id != request.user.pk:
            return Response(
                {'success': False, 'error': 'Only the host can cancel confirmation.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if post.event_status != Post.STATUS_CONFIRMED:
            return Response(
                {'success': False, 'error': 'This event is not confirmed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _reopen_confirmed_event(post, request.user)
        post.refresh_from_db()
        return Response({
            'success': True,
            'event_status': post.event_status,
            'thread': get_thread_meta(conv, request.user),
        })


class OpenConversationAPIView(APIView):
    """Open or create a DM for a post (optionally with a specific peer)."""

    permission_classes = [IsEmailVerified]

    def post(self, request):
        ser = OpenConversationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        post = get_object_or_404(Post, pk=ser.validated_data['post_id'])
        username = (ser.validated_data.get('username') or '').strip()
        if username:
            peer = get_object_or_404(User, username=username)
        else:
            peer = post.author
        if not peer or peer.pk == request.user.pk:
            return Response(
                {'success': False, 'error': 'Invalid conversation target.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.pk not in (post.author_id, peer.pk):
            return Response(
                {'success': False, 'error': 'You cannot start this conversation.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        conv, created = get_or_create_dm(post, request.user, peer)
        return Response({
            'success': True,
            'created': created,
            'conversation_id': conv.id,
            'thread': get_thread_meta(conv, request.user),
        })
