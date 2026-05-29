from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.verification_session import stash_pending_verification


class EmailVerificationMiddleware:
    """Redirect unverified users away from the dashboard."""

    ALLOWED_PREFIXES = (
        '/accounts/verify-account',
        '/accounts/verify-email',
        '/accounts/verify-phone',
        '/accounts/verify/',
        '/accounts/login',
        '/accounts/logout',
        '/accounts/signup',
        '/static/',
        '/media/',
        '/admin/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if not request.user.is_email_verified:
                path = request.path
                if not any(path.startswith(p) for p in self.ALLOWED_PREFIXES):
                    if profile is not None:
                        stash_pending_verification(request, request.user, profile)
                    return redirect(reverse('accounts:verify_account'))
        return self.get_response(request)
