from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.permissions import IsEmailVerified
from apps.api.serializers import PostCommentCreateSerializer, PostSerializer
from apps.api.services.engagement import EngagementError, add_post_comment, toggle_post_interest, toggle_post_reaction
from apps.core.engagement import build_comment_tree, posts_with_engagement
from apps.core.forms import UserPostForm
from apps.core.models import Post
from apps.core.messenger_views import confirm_post_match, _reopen_confirmed_event


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsEmailVerified]
    lookup_field = 'pk'

    def get_queryset(self):
        qs = posts_with_engagement(self.request.user)
        time_slug = self.request.query_params.get('time')
        if time_slug:
            qs = qs.filter(time__slug=time_slug)
        author = self.request.query_params.get('author')
        if author == 'me':
            qs = qs.filter(author=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author_id != request.user.pk:
            return Response(
                {'success': False, 'error': 'You are not authorized to update this post.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = request.data.copy()
        for src, dest in (('location_id', 'location'), ('venue_id', 'venue'), ('time_id', 'time')):
            if src in data and dest not in data:
                data[dest] = data[src]
        form = UserPostForm(data, instance=post)
        if not form.is_valid():
            return Response({'success': False, 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)
        form.save()
        post = posts_with_engagement(request.user).get(pk=post.pk)
        return Response({
            'success': True,
            'post': PostSerializer(post, context={'request': request}).data,
        })

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author_id != request.user.pk:
            return Response(
                {'success': False, 'error': 'You are not authorized to delete this post.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        post.delete()
        return Response({'success': True, 'message': 'Match deleted successfully.'})

    @action(detail=True, methods=['post'])
    def interest(self, request, pk=None):
        post = self.get_object()
        try:
            data = toggle_post_interest(post, request.user)
        except EngagementError as e:
            return Response(
                {'success': False, 'error': e.message, 'locked': e.locked},
                status=e.status_code,
            )
        return Response({'success': True, **data})

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        post = self.get_object()
        try:
            data = toggle_post_reaction(post, request.user)
        except EngagementError as e:
            return Response(
                {'success': False, 'error': e.message, 'locked': e.locked},
                status=e.status_code,
            )
        return Response({'success': True, **data})

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        post = self.get_object()
        return Response({
            'success': True,
            'comments': build_comment_tree(post.pk),
        })

    @action(detail=True, methods=['post'], url_path='comments/add')
    def add_comment(self, request, pk=None):
        post = self.get_object()
        ser = PostCommentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = add_post_comment(
                post, request.user,
                ser.validated_data['body'],
                ser.validated_data.get('parent_id'),
            )
        except EngagementError as e:
            return Response(
                {'success': False, 'error': e.message, 'locked': e.locked},
                status=e.status_code,
            )
        return Response({'success': True, **data})

    @action(detail=True, methods=['post'], url_path='confirm-match')
    def confirm_match(self, request, pk=None):
        post = self.get_object()
        try:
            confirm_post_match(post, request.user)
        except PermissionError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        post.refresh_from_db()
        return Response({'success': True, 'event_status': post.event_status})

    @action(detail=True, methods=['post'], url_path='cancel-confirmation')
    def cancel_confirmation(self, request, pk=None):
        post = self.get_object()
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
        return Response({'success': True, 'event_status': post.event_status})
