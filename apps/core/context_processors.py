from futnetnepal.youtube import youtube_embed_url


def site_content(request):
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
