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
    """Render 500 without request context processors (DB may be down)."""
    path = getattr(request, 'path', '')
    logger.exception('Unhandled server error%s', f' for {path}' if path else '')

    template = loader.get_template('500.html')
    body = template.render({
        'site_name': 'Futnet Nepal',
        'path': path,
    })
    return HttpResponse(body, status=500)
