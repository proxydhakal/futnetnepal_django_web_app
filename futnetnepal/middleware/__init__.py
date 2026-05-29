from futnetnepal.audit import get_audit_user, reset_audit_user, set_audit_user


class AuditContextMiddleware:
    """Expose request.user to model save/delete for audit FK fields."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        token = None
        if user is not None and user.is_authenticated:
            token = set_audit_user(user)
        try:
            return self.get_response(request)
        finally:
            if token is not None:
                reset_audit_user(token)
