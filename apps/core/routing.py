from django.urls import re_path

from apps.core import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/dm/(?P<conversation_id>\d+)/$', consumers.DmChatConsumer.as_asgi()),
    # Cached clients may still use the old event-wide path; maps to private DM.
    re_path(r'ws/events/(?P<post_id>\d+)/chat/$', consumers.LegacyEventChatConsumer.as_asgi()),
]
