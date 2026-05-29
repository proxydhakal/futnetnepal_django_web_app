"""Custom HTTP error pages (used when DEBUG=False)."""

import logging

from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

logger = logging.getLogger(__name__)


def page_not_found(request, exception):
    return render(
        request,
        '404.html',
        {
            'path': request.path,
            'exception': exception,
        },
        status=404,
    )


def server_error(request):
    """Render 500; fall back to a minimal template if context processors or DB fail."""
    path = getattr(request, 'path', '')
    logger.exception('Unhandled server error%s', f' for {path}' if path else '')

    try:
        return render(request, '500.html', {'path': path}, status=500)
    except Exception:
        logger.exception('500 fallback template (site layout unavailable)')
        template = loader.get_template('500_standalone.html')
        body = template.render({'path': path})
        return HttpResponse(body, status=500)
