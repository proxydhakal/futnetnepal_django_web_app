import logging

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
