"""DRF exception handler with structured error logging."""

import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger('futnetnepal.request')


def logged_api_exception_handler(exc, context):
    """Log API failures, then delegate to DRF's default handler."""
    request = context.get('view').request if context.get('view') else None
    view = context.get('view')
    view_name = type(view).__name__ if view else 'unknown'

    if request is not None:
        rid = getattr(request, 'request_id', '-')
        user = getattr(request, 'user', None)
        username = getattr(user, 'username', '-') if user and user.is_authenticated else '-'
        logger.error(
            'API exception rid=%s view=%s %s %s user=%s | %s: %s',
            rid,
            view_name,
            request.method,
            request.path,
            username,
            type(exc).__name__,
            exc,
            exc_info=exc,
        )
    else:
        logger.error(
            'API exception view=%s | %s: %s',
            view_name,
            type(exc).__name__,
            exc,
            exc_info=exc,
        )

    response = drf_exception_handler(exc, context)
    if response is not None and request is not None:
        logger.warning(
            'API error response rid=%s %s %s status=%s data=%s',
            getattr(request, 'request_id', '-'),
            request.method,
            request.path,
            response.status_code,
            response.data,
        )
    return response
