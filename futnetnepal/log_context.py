"""Per-request correlation id for log lines (HTTP + background tasks)."""

import uuid
from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar('request_id', default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def set_request_id(request_id: str | None):
    return _request_id.set(request_id)


def get_request_id() -> str | None:
    return _request_id.get()


def reset_request_id(token):
    _request_id.reset(token)
