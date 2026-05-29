"""Rules for locking identity fields after verification."""

from django.core.exceptions import ValidationError

from apps.accounts.phone_verification import PhoneVerificationError, normalize_phone

LOCKED_USERNAME_MSG = 'Username cannot be changed.'
LOCKED_EMAIL_MSG = 'Verified email cannot be changed.'
LOCKED_PHONE_MSG = 'Verified phone number cannot be changed.'


def reject_username_change(user, new_username) -> None:
    if new_username is None:
        return
    if new_username != user.username:
        raise ValidationError(LOCKED_USERNAME_MSG)


def reject_email_change(user, new_email) -> None:
    if new_email is None or not user.is_email_verified:
        return
    if (new_email or '').strip().lower() != user.email.lower():
        raise ValidationError(LOCKED_EMAIL_MSG)


def reject_phone_change(profile, new_phone) -> None:
    if new_phone is None or not profile.phone_verified:
        return
    raw = (new_phone or '').strip()
    if not raw:
        raise ValidationError(LOCKED_PHONE_MSG)
    try:
        normalized = normalize_phone(raw)
    except PhoneVerificationError as exc:
        raise ValidationError(str(exc)) from exc
    if normalized != profile.phone:
        raise ValidationError(LOCKED_PHONE_MSG)
