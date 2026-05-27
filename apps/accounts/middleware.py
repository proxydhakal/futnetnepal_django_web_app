from django.shortcuts import redirect
from django.urls import reverse


class EmailVerificationMiddleware:
    """Redirect unverified users away from the dashboard."""

    ALLOWED_PREFIXES = (
        '/accounts/verify-email',
        '/accounts/verify/',
        '/accounts/logout',
        '/static/',
        '/media/',
        '/admin/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile is not None and not profile.email_verified:
                path = request.path
                if not any(path.startswith(p) for p in self.ALLOWED_PREFIXES):
                    return redirect(reverse('accounts:verify_email_pending'))
        return self.get_response(request)
