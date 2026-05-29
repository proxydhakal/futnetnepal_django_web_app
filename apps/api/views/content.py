"""Public site content APIs (CMS, newsletter, reviews) — mirrors web template views."""

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.serializers import (
    CMSPageDetailSerializer,
    CMSPageListSerializer,
    NewsletterSubscribeSerializer,
    SiteConfigurationPublicSerializer,
    UserReviewCreateSerializer,
    UserReviewPublicSerializer,
)
from apps.blogs.models import Blog
from apps.core.models import CMSPage, SiteConfiguration, UserReview


class SiteConfigurationAPIView(APIView):
    """Singleton branding + page copy (same data as template context `site_config`)."""

    permission_classes = [AllowAny]

    def get(self, request):
        config = SiteConfiguration.get_solo()
        return Response({
            'success': True,
            'site': SiteConfigurationPublicSerializer(
                config, context={'request': request},
            ).data,
        })


class PublicHomeAPIView(APIView):
    """Landing page data: approved reviews (matches `index` view)."""

    permission_classes = [AllowAny]

    def get(self, request):
        limit = min(int(request.query_params.get('limit', 6) or 6), 24)
        reviews = UserReview.objects.filter(is_approved=True).order_by('-created_at')[:limit]
        return Response({
            'success': True,
            'approved_reviews': UserReviewPublicSerializer(
                reviews, many=True, context={'request': request},
            ).data,
        })


class CMSPageViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        qs = CMSPage.objects.filter(is_published=True, is_deleted=False)
        if self.request.query_params.get('navbar') in ('1', 'true', 'yes'):
            qs = qs.filter(show_in_navbar=True)
        if self.request.query_params.get('footer') in ('1', 'true', 'yes'):
            qs = qs.filter(show_in_footer=True)
        return qs.order_by('sort_order', 'title')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CMSPageDetailSerializer
        return CMSPageListSerializer


class NewsletterSubscribeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NewsletterSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        return Response({
            'success': True,
            'message': (
                'Thanks for subscribing! Check your inbox for a confirmation email.'
            ),
        }, status=status.HTTP_201_CREATED)


class UserReviewAPIView(APIView):
    """List approved reviews (GET) or submit a new review (POST)."""

    permission_classes = [AllowAny]

    def get(self, request):
        limit = request.query_params.get('limit')
        qs = UserReview.objects.filter(is_approved=True).order_by('-created_at')
        if limit:
            try:
                qs = qs[: max(1, min(int(limit), 100))]
            except (TypeError, ValueError):
                pass
        return Response({
            'success': True,
            'reviews': UserReviewPublicSerializer(
                qs, many=True, context={'request': request},
            ).data,
        })

    def post(self, request):
        serializer = UserReviewCreateSerializer(
            data=request.data, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response({
            'success': True,
            'message': (
                'Thank you! Your review was submitted and will appear on the site '
                'after our team approves it.'
            ),
            'review_id': review.pk,
        }, status=status.HTTP_201_CREATED)
