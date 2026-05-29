"""Log every HTTP request/response (trimmed) for web pages and REST API."""

import logging
import time

from django.http import HttpRequest, HttpResponse

from futnetnepal.env import env_bool, env_int
from futnetnepal.log_context import new_request_id, reset_request_id, set_request_id
from futnetnepal.logging_utils import (
    is_api_request,
    parse_request_body,
    parse_response_body,
    request_log_context,
    should_skip_request_logging,
)

logger = logging.getLogger('futnetnepal.request')

BODY_MAX = env_int('LOG_BODY_MAX_CHARS', default=2048)
LOG_REQUEST_BODY = env_bool('LOG_REQUEST_BODY', default=True)
LOG_RESPONSE_BODY = env_bool('LOG_RESPONSE_BODY', default=True)


class RequestLoggingMiddleware:
    """
    One correlation id (rid) per request; logs inbound + outbound with duration.
    API: JSON bodies trimmed/redacted. Web: HTML summarized by byte size.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if should_skip_request_logging(request):
            return self.get_response(request)

        request_id = new_request_id()
        token = set_request_id(request_id)
        request.request_id = request_id  # type: ignore[attr-defined]

        api = is_api_request(request)
        kind = 'API' if api else 'WEB'
        started = time.perf_counter()
        ctx = request_log_context(request)

        req_body = None
        if LOG_REQUEST_BODY:
            req_body = parse_request_body(request, max_chars=BODY_MAX)

        parts = [
            f'{kind} → {ctx["method"]} {ctx["path"]}',
            f'ip={ctx["ip"]} user={ctx["username"]}({ctx["user_id"]})',
        ]
        if ctx['query']:
            parts.append(f'query={ctx["query"]}')
        if req_body:
            parts.append(f'body={req_body}')
        logger.info(' | '.join(parts))

        try:
            response = self.get_response(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                '%s ✗ %s %s | %.1fms | unhandled exception',
                kind, ctx['method'], ctx['path'], elapsed_ms,
            )
            reset_request_id(token)
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        status = response.status_code
        level = logging.INFO
        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING

        resp_parts = [
            f'{kind} ← {ctx["method"]} {ctx["path"]}',
            f'status={status} duration={elapsed_ms:.1f}ms',
            f'user={ctx["username"]}({ctx["user_id"]})',
        ]
        if LOG_RESPONSE_BODY:
            preview = parse_response_body(response, max_chars=BODY_MAX, api=api)
            if preview:
                resp_parts.append(f'body={preview}')

        logger.log(level, ' | '.join(resp_parts))
        response['X-Request-ID'] = request_id
        reset_request_id(token)
        return response
