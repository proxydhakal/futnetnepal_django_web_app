"""Live password checklist for signup (mirrors AUTH_PASSWORD_VALIDATORS)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
    get_password_validators,
)
from django.core.exceptions import ValidationError


User = get_user_model()


def user_for_password_check(*, username='', email='', full_name=''):
    return User(
        username=(username or '').strip(),
        email=(email or '').strip().lower(),
        full_name=(full_name or '').strip(),
    )


def _min_password_length():
    for validator in get_password_validators(settings.AUTH_PASSWORD_VALIDATORS):
        if isinstance(validator, MinimumLengthValidator):
            return validator.min_length
    return 8


def _validator_ok(validator, password, user):
    try:
        validator.validate(password, user)
        return True
    except ValidationError:
        return False


def password_suggestions(password, user=None):
    """
    Return checklist items: {id, text, ok} where ok is True/False when password
    is non-empty, or None when password is empty (pending).
    """
    check_user = user or User()
    pending = password == ''
    min_len = _min_password_length()

    def status(passed):
        if pending:
            return None
        return passed

    similar = _validator_ok(UserAttributeSimilarityValidator(), password, check_user)
    common = _validator_ok(CommonPasswordValidator(), password, check_user)
    numeric = _validator_ok(NumericPasswordValidator(), password, check_user)
    length_ok = len(password) >= min_len

    return [
        {
            'id': 'similar',
            'text': 'Not too similar to your other personal information.',
            'ok': status(similar),
        },
        {
            'id': 'length',
            'text': f'Use at least {min_len} characters.',
            'ok': status(length_ok),
        },
        {
            'id': 'common',
            'text': 'Avoid commonly used passwords.',
            'ok': status(common),
        },
        {
            'id': 'numeric',
            'text': 'Cannot be entirely numeric.',
            'ok': status(numeric),
        },
    ]


def password_is_valid(password, user=None):
    if not password:
        return False
    suggestions = password_suggestions(password, user=user)
    return all(s['ok'] for s in suggestions)
