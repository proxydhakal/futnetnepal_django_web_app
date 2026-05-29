"""Thread-safe current user for model audit fields (created_by / updated_by / deleted_by)."""

from contextlib import contextmanager
from contextvars import ContextVar

_audit_user: ContextVar = ContextVar('audit_user', default=None)


def get_audit_user():
    return _audit_user.get()


def set_audit_user(user):
    return _audit_user.set(user)


def reset_audit_user(token):
    _audit_user.reset(token)


@contextmanager
def audit_user(user):
    """Set audit user for ORM operations inside this block (e.g. Channels workers)."""
    token = set_audit_user(user)
    try:
        yield
    finally:
        reset_audit_user(token)


def _valid_audit_user(user):
    return user is not None and getattr(user, 'pk', None)
