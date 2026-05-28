from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api.views.auth import (
    LoginAPIView,
    MeAPIView,
    PasswordChangeAPIView,
    PasswordResetConfirmAPIView,
    PasswordResetRequestAPIView,
    PhoneSendOtpAPIView,
    PhoneVerifyOtpAPIView,
    RegisterAPIView,
    ResendVerificationAPIView,
    VerificationStatusAPIView,
    TokenRefreshAPIView,
    VerifyEmailAPIView,
)
from apps.api.views.messages import ConversationViewSet, OpenConversationAPIView
from apps.api.views.misc import (
    BlogViewSet,
    CategoryViewSet,
    ContactAPIView,
    LocationViewSet,
    NotificationMarkAllReadAPIView,
    NotificationMarkReadAPIView,
    NotificationPollAPIView,
    NotificationViewSet,
    ProfileStatsAPIView,
    SearchAPIView,
    TimeViewSet,
    VenueBookingViewSet,
    VenueViewSet,
)
from apps.api.views.posts import PostViewSet

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='api-location')
router.register(r'times', TimeViewSet, basename='api-time')
router.register(r'venues', VenueViewSet, basename='api-venue')
router.register(r'posts', PostViewSet, basename='api-post')
router.register(r'bookings', VenueBookingViewSet, basename='api-booking')
router.register(r'notifications', NotificationViewSet, basename='api-notification')
router.register(r'conversations', ConversationViewSet, basename='api-conversation')
router.register(r'blogs', BlogViewSet, basename='api-blog')
router.register(r'blog-categories', CategoryViewSet, basename='api-blog-category')

urlpatterns = [
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/token/refresh/', TokenRefreshAPIView.as_view(), name='api-token-refresh'),
    path('auth/verification-status/', VerificationStatusAPIView.as_view(), name='api-verification-status'),
    path('auth/verify-email/', VerifyEmailAPIView.as_view(), name='api-verify-email'),
    path('auth/phone/send-otp/', PhoneSendOtpAPIView.as_view(), name='api-phone-send-otp'),
    path('auth/phone/verify/', PhoneVerifyOtpAPIView.as_view(), name='api-phone-verify'),
    path('auth/resend-verification/', ResendVerificationAPIView.as_view(), name='api-resend-verification'),
    path('auth/me/', MeAPIView.as_view(), name='api-me'),
    path('auth/password/change/', PasswordChangeAPIView.as_view(), name='api-password-change'),
    path('auth/password/reset/', PasswordResetRequestAPIView.as_view(), name='api-password-reset'),
    path('auth/password/reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='api-password-reset-confirm'),
    path('profile/stats/', ProfileStatsAPIView.as_view(), name='api-profile-stats'),
    path('search/', SearchAPIView.as_view(), name='api-search'),
    path('contact/', ContactAPIView.as_view(), name='api-contact'),
    path('conversations/open/', OpenConversationAPIView.as_view(), name='api-conversation-open'),
    path(
        'notifications/<int:notification_id>/read/',
        NotificationMarkReadAPIView.as_view(),
        name='api-notification-read',
    ),
    path(
        'notifications/read-all/',
        NotificationMarkAllReadAPIView.as_view(),
        name='api-notifications-read-all',
    ),
    path('notifications/poll/', NotificationPollAPIView.as_view(), name='api-notifications-poll'),
    path('', include(router.urls)),
]
