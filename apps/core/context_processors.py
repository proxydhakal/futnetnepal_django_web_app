import logging

from django.db.models import Count

from futnetnepal.youtube import youtube_embed_url

logger = logging.getLogger(__name__)


def _empty_site_config():
    """Minimal stand-in when SiteConfiguration cannot be loaded (e.g. 500 / DB down)."""
    return type('EmptySiteConfig', (), {
        'contact_phone': '',
        'contact_email': '',
        'logo': None,
        'favicon': None,
        'site_title': 'Futnet Nepal',
    })()


def site_content(request):
    try:
        from apps.core.models import CMSPage, SiteConfiguration

        config = SiteConfiguration.get_solo()
        published = CMSPage.objects.filter(is_published=True, is_deleted=False)
        return {
            'site_config': config,
            'site_content': config,
            'about_youtube_embed': youtube_embed_url(config.about_youtube_url),
            'home_youtube_embed': youtube_embed_url(config.home_youtube_url),
            'navbar_cms_pages': published.filter(show_in_navbar=True).order_by(
                'sort_order', 'title',
            ),
            'footer_cms_pages': published.filter(show_in_footer=True).order_by(
                'sort_order', 'title',
            ),
        }
    except Exception:
        logger.exception('Unable to load site configuration for templates')
        empty = _empty_site_config()
        return {
            'site_config': empty,
            'site_content': empty,
            'about_youtube_embed': '',
            'home_youtube_embed': '',
            'navbar_cms_pages': [],
            'footer_cms_pages': [],
        }


def _platform_stats():
    from django.contrib.auth import get_user_model

    from apps.core.models import Location, Post, Venue

    User = get_user_model()
    return {
        'matches': Post.objects.count(),
        'players': User.objects.count(),
        'venues': Venue.objects.count(),
        'cities': Location.objects.count(),
    }


def _dashboard_active(request):
    match = getattr(request, 'resolver_match', None)
    if not match:
        return 'feed'
    name = match.url_name or ''
    namespace = match.namespace or ''
    if namespace == 'accounts':
        if name == 'profile':
            return 'profile'
        if name in ('password_change', 'password_change_done'):
            return 'settings'
        if name == 'verify_account':
            return 'profile'
    if name in ('venuelist', 'venue_detail'):
        return 'venues'
    if name in ('messages', 'messages_conversation', 'messages_thread', 'messages_with_user'):
        return 'messages'
    if name in ('home', 'post-cat'):
        return 'feed'
    return ''


def dashboard_shell(request):
    """Shared sidebar/header context for authenticated app pages."""
    if not request.user.is_authenticated:
        return {}
    try:
        from apps.accounts.stats import user_profile_stats
        from apps.core.forms import UserPostForm
        from apps.core.models import Time, Venue

        return {
            'stats': user_profile_stats(request.user),
            'platform_stats': _platform_stats(),
            'times': Time.objects.values('id', 'name', 'slug').annotate(total=Count('post')),
            'featured_venues': Venue.objects.select_related('location').order_by('name')[:5],
            'dashboard_active': _dashboard_active(request),
            'create_form': UserPostForm(),
        }
    except Exception:
        logger.exception('Unable to load dashboard shell context')
        return {}
