import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from django.db.models import Q

from futnetnepal.audit import audit_user

from apps.core.models import DirectConversation, Post

ws_logger = logging.getLogger('futnetnepal.request')


def _safe_message_body(raw):
    from django.core.exceptions import ValidationError as DjangoValidationError
    from futnetnepal.input_validation import sanitize_plain_text

    try:
        return sanitize_plain_text(
            raw or '',
            max_length=1000,
            multiline=True,
            min_length=1,
            field_label='Message',
        )
    except DjangoValidationError:
        return ''


class NotificationConsumer(AsyncWebsocketConsumer):
    """Per-user WebSocket for live notifications."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.group_name = f'user_notifications_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        ws_logger.info(
            'WS connect notifications user=%s(%s)',
            user.username,
            user.pk,
        )
        await self.send(text_data=json.dumps({
            'event': 'connected',
            'message': 'Notifications connected',
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        ws_logger.info('WS disconnect notifications code=%s', close_code)

    async def push_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))


class DmChatConsumer(AsyncWebsocketConsumer):
    """Private 1:1 conversation WebSocket."""

    async def connect(self):
        user = self.scope['user']
        self.conversation_id = int(self.scope['url_route']['kwargs']['conversation_id'])
        if not user.is_authenticated:
            await self.close()
            return
        allowed = await self._can_access(self.conversation_id, user)
        if not allowed:
            await self.close()
            return
        self.group_name = f'dm_{self.conversation_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        ws_logger.info(
            'WS connect dm user=%s(%s) conversation=%s',
            user.username,
            user.pk,
            self.conversation_id,
        )
        await self.send(text_data=json.dumps({
            'event': 'connected',
            'conversation_id': self.conversation_id,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        ws_logger.info('WS disconnect dm conversation=%s code=%s', getattr(self, 'conversation_id', '-'), close_code)

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get('action') == 'send_message':
            body = self._safe_message_body(data.get('body'))
            if body:
                result = await self._send_message(self.conversation_id, user, body)
                if result and result.get('error'):
                    await self.send(text_data=json.dumps({
                        'event': 'error',
                        'message': result['error'],
                    }))

    async def push_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    @database_sync_to_async
    def _can_access(self, conversation_id, user):
        from apps.core.chat import user_can_access_dm
        try:
            conv = DirectConversation.objects.get(pk=conversation_id)
        except DirectConversation.DoesNotExist:
            return False
        return user_can_access_dm(conv, user)

    @database_sync_to_async
    def _send_message(self, conversation_id, user, body):
        from django.shortcuts import get_object_or_404
        from apps.core.chat import user_can_access_dm
        from apps.core.messenger_views import _send_dm_and_broadcast

        from apps.core.event_guard import is_event_locked

        conv = get_object_or_404(DirectConversation.objects.select_related('post'), pk=conversation_id)
        if not user_can_access_dm(conv, user):
            return {'error': 'Access denied.'}
        if is_event_locked(conv.post):
            return {'error': 'This match is confirmed. Chat is closed.'}
        with audit_user(user):
            try:
                _send_dm_and_broadcast(conv, user, body)
            except ValueError:
                return {'error': 'This match is confirmed. Chat is closed.'}
        return {'success': True}


class LegacyEventChatConsumer(AsyncWebsocketConsumer):
    """
    Back-compat: old clients connect to /ws/events/<post_id>/chat/.
    Joins the private DM channel for this user on that post.
    """

    async def connect(self):
        user = self.scope['user']
        self.post_id = self.scope['url_route']['kwargs']['post_id']
        if not user.is_authenticated:
            await self.close()
            return
        conv = await self._resolve_conversation(self.post_id, user)
        if not conv:
            await self.close()
            return
        self.conversation_id = conv.id
        self.group_name = f'dm_{self.conversation_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'event': 'connected',
            'conversation_id': self.conversation_id,
            'legacy': True,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated or not hasattr(self, 'conversation_id'):
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get('action') == 'send_message':
            body = _safe_message_body(data.get('body'))
            if body:
                result = await DmChatConsumer._send_message(
                    self, self.conversation_id, user, body,
                )
                if result and result.get('error'):
                    await self.send(text_data=json.dumps({
                        'event': 'error',
                        'message': result['error'],
                    }))

    async def push_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    @database_sync_to_async
    def _resolve_conversation(self, post_id, user):
        from apps.core.chat import get_or_create_dm, user_can_access_dm

        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return None
        if post.author_id == user.pk:
            conv = (
                DirectConversation.objects.filter(post=post)
                .filter(Q(user_a=user) | Q(user_b=user))
                .order_by('-updated_at')
                .first()
            )
        elif post.author_id:
            conv, _ = get_or_create_dm(post, user, post.author)
        else:
            return None
        if conv and user_can_access_dm(conv, user):
            return conv
        return None
