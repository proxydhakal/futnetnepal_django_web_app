from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with username or email (case-insensitive)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        login_value = kwargs.get('login') or username
        if not login_value or password is None:
            return None

        user = self._get_user_by_login(login_value)
        if user is None:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _get_user_by_login(self, login_value):
        User = get_user_model()
        login_value = login_value.strip()
        try:
            if '@' in login_value:
                return User.objects.get(email__iexact=login_value)
            return User.objects.get(username__iexact=login_value)
        except User.DoesNotExist:
            return None
