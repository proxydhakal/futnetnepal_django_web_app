from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    message = 'Please verify your email and phone before using the app.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        if not request.user.is_email_verified:
            return False
        if profile.phone and not profile.phone_verified:
            return False
        return True
