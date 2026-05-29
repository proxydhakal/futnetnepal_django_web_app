from django.contrib.auth import get_user_model

User = get_user_model()
from django.db.models import F, Q
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import IsEmailVerified
from apps.api.serializers import (
    BlogDetailSerializer,
    BlogListSerializer,
    CategorySerializer,
    ContactSerializer,
    LocationSerializer,
    NotificationSerializer,
    SearchQuerySerializer,
    TimeSerializer,
    UserBriefSerializer,
    VenueBookingSerializer,
    VenueSerializer,
)
from apps.accounts.stats import user_profile_stats
from apps.blogs.models import Blog, Category
from apps.core.models import Location, Notification, Post, Time, Venue, VenueBooking
from apps.core.realtime import push_unread_count, serialize_notification


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [IsEmailVerified]


class TimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Time.objects.all().order_by('name')
    serializer_class = TimeSerializer
    permission_classes = [IsEmailVerified]


class VenueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Venue.objects.select_related('location').all().order_by('name')
    serializer_class = VenueSerializer
    permission_classes = [IsEmailVerified]
    lookup_field = 'slug'


class VenueBookingViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = VenueBookingSerializer
    permission_classes = [IsEmailVerified]

    def get_queryset(self):
        return VenueBooking.objects.filter(
            user=self.request.user,
        ).select_related('venue', 'venue__location', 'time_slot').order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response({
            'success': True,
            'message': 'Booking request submitted! We will confirm shortly.',
            'booking': self.get_serializer(booking).data,
        }, status=status.HTTP_201_CREATED)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsEmailVerified]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        ).select_related('actor', 'post').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        unread_count = self.get_queryset().filter(is_read=False).count()
        if isinstance(response.data, dict) and 'results' in response.data:
            response.data['unread_count'] = unread_count
            response.data['success'] = True
        else:
            response.data = {
                'success': True,
                'unread_count': unread_count,
                'notifications': response.data,
            }
        return response

    @staticmethod
    def _mark_read(request, notification_id):
        exists = Notification.objects.filter(
            pk=notification_id, recipient=request.user,
        ).exists()
        if not exists:
            return False
        updated = Notification.objects.filter(
            pk=notification_id, recipient=request.user, is_read=False,
        ).update(is_read=True)
        if updated:
            push_unread_count(request.user.pk)
        return True

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._mark_read(request, instance.pk)
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'notification': serializer.data})


class NotificationMarkReadAPIView(APIView):
    permission_classes = [IsEmailVerified]

    def post(self, request, notification_id):
        if not NotificationViewSet._mark_read(request, notification_id):
            return Response(
                {'success': False, 'error': 'Notification not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        unread = Notification.objects.filter(
            recipient=request.user, is_read=False,
        ).count()
        return Response({'success': True, 'unread_count': unread})

    def patch(self, request, notification_id):
        return self.post(request, notification_id)


class NotificationMarkAllReadAPIView(APIView):
    permission_classes = [IsEmailVerified]

    def post(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False,
        ).update(is_read=True)
        push_unread_count(request.user.pk)
        return Response({'success': True, 'unread_count': 0})


class NotificationPollAPIView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request):
        since_id = int(request.query_params.get('since_id', 0) or 0)
        qs = Notification.objects.filter(recipient=request.user).select_related('actor', 'post')
        unread_count = qs.filter(is_read=False).count()
        new_items = qs.filter(id__gt=since_id)[:20]
        return Response({
            'success': True,
            'unread_count': unread_count,
            'notifications': [serialize_notification(n) for n in new_items],
        })


class BlogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        qs = Blog.objects.select_related('category', 'author').prefetch_related('tags')
        category = self.request.query_params.get('category')
        if category:
            if str(category).isdigit():
                qs = qs.filter(category_id=int(category))
            else:
                qs = qs.filter(category__title__iexact=category)
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BlogDetailSerializer
        return BlogListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Blog.objects.filter(pk=instance.pk).update(count=F('count') + 1)
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        related = Blog.objects.exclude(pk=instance.pk).order_by('-count')[:2]
        return Response({
            'success': True,
            'blog': serializer.data,
            'related_blogs': BlogListSerializer(
                related, many=True, context={'request': request},
            ).data,
        })


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('title')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class SearchAPIView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request):
        ser = SearchQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        q = ser.validated_data['q']
        posts = Post.objects.filter(
            Q(message__icontains=q) | Q(venue__name__icontains=q) | Q(location__name__icontains=q),
        ).select_related('venue', 'location', 'author')[:8]
        venues = Venue.objects.filter(
            Q(name__icontains=q) | Q(address__icontains=q),
        )[:5]
        users = User.objects.filter(
            Q(username__icontains=q) | Q(full_name__icontains=q) | Q(email__icontains=q),
        ).exclude(pk=request.user.pk)[:5]
        blogs = Blog.objects.filter(
            Q(title__icontains=q) | Q(content__icontains=q),
        ).select_related('category', 'author')[:5]
        return Response({
            'success': True,
            'posts': [
                {
                    'id': str(p.id),
                    'slug': p.slug,
                    'title': (p.message[:60] + '...') if len(p.message) > 60 else p.message,
                    'subtitle': f'{p.venue} · {p.author.username if p.author else "Unknown"}',
                }
                for p in posts
            ],
            'venues': VenueSerializer(venues, many=True, context={'request': request}).data,
            'users': UserBriefSerializer(users, many=True, context={'request': request}).data,
            'blogs': BlogListSerializer(blogs, many=True, context={'request': request}).data,
        })


class ProfileStatsAPIView(APIView):
    permission_classes = [IsEmailVerified]

    def get(self, request):
        return Response({'success': True, 'stats': user_profile_stats(request.user)})


class ContactAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'success': True,
            'message': 'Message submitted successfully.',
        }, status=status.HTTP_201_CREATED)
