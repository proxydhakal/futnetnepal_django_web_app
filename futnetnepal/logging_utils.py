"""Trim and redact data before writing to logs."""

import json
import re
from typing import Any

from django.http import HttpRequest, HttpResponse

SENSITIVE_KEY_RE = re.compile(
    r'(password|passwd|token|secret|authorization|csrf|cookie|otp|code|'
    r'access|refresh|api[_-]?key|session)',
    re.IGNORECASE,
)

SKIP_PATH_PREFIXES = (
    '/static/',
    '/media/',
    '/favicon.ico',
)

SKIP_LOG_EXTENSIONS = ('.ico', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.css', '.js', '.map', '.woff', '.woff2')


def should_skip_request_logging(request: HttpRequest) -> bool:
    path = request.path or ''
    if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
        return True
    if path.endswith(SKIP_LOG_EXTENSIONS):
        return True
    return False


def is_api_request(request: HttpRequest) -> bool:
    path = request.path or ''
    if path.startswith('/api/'):
        return True
    accept = request.META.get('HTTP_ACCEPT', '')
    return 'application/json' in accept and 'text/html' not in accept


def client_ip(request: HttpRequest) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '-')


def trim_text(value: str, *, max_chars: int) -> str:
    if not value:
        return ''
    text = value.replace('\r\n', '\n').replace('\r', '\n')
    if len(text) <= max_chars:
        return text
    return f'{text[:max_chars]}…[+{len(text) - max_chars} chars]'


def redact_sensitive(data: Any) -> Any:
    if isinstance(data, dict):
        out = {}
        for key, val in data.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                out[key] = '***'
            else:
                out[key] = redact_sensitive(val)
        return out
    if isinstance(data, list):
        return [redact_sensitive(item) for item in data]
    return data


def parse_request_body(request: HttpRequest, *, max_chars: int) -> str | None:
    content_type = (request.content_type or '').split(';')[0].strip().lower()
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    if content_type.startswith('multipart/'):
        return '<multipart/form-data>'
    try:
        raw = request.body
    except Exception:
        return '<unreadable body>'
    if not raw:
        return None
    if content_type == 'application/json' or raw[:1] in (b'{', b'['):
        try:
            payload = json.loads(raw.decode('utf-8'))
            payload = redact_sensitive(payload)
            return trim_text(json.dumps(payload, ensure_ascii=False, default=str), max_chars=max_chars)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    try:
        text = raw.decode('utf-8', errors='replace')
    except Exception:
        return f'<binary {len(raw)} bytes>'
    return trim_text(text, max_chars=max_chars)


def parse_response_body(response: HttpResponse, *, max_chars: int, api: bool) -> str | None:
    content_type = (response.get('Content-Type') or '').split(';')[0].strip().lower()
    if not hasattr(response, 'content'):
        return '<streaming response>'
    content = response.content or b''
    if not content:
        return None
    if 'text/html' in content_type and not api:
        return f'<html {len(content)} bytes>'
    if content_type.startswith('multipart/'):
        return '<multipart>'
    if 'application/json' in content_type or content[:1] in (b'{', b'['):
        try:
            payload = json.loads(content.decode('utf-8'))
            payload = redact_sensitive(payload)
            return trim_text(json.dumps(payload, ensure_ascii=False, default=str), max_chars=max_chars)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    try:
        text = content.decode('utf-8', errors='replace')
    except Exception:
        return f'<binary {len(content)} bytes>'
    return trim_text(text, max_chars=max_chars)


def request_log_context(request: HttpRequest) -> dict[str, Any]:
    user = getattr(request, 'user', None)
    username = '-'
    user_id = '-'
    if user is not None and getattr(user, 'is_authenticated', False):
        username = getattr(user, 'username', str(user.pk))
        user_id = str(user.pk)
    query = request.META.get('QUERY_STRING', '')
    return {
        'method': request.method,
        'path': request.path,
        'query': trim_text(query, max_chars=500) if query else '',
        'ip': client_ip(request),
        'user_id': user_id,
        'username': username,
        'content_type': request.content_type or '',
        'content_length': request.META.get('CONTENT_LENGTH', ''),
    }
