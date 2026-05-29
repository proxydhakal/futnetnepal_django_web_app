import logging
import random

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.accounts.models import Profile

logger = logging.getLogger(__name__)


class EmailVerificationError(Exception):
    def __init__(self, message, code='invalid'):
        super().__init__(message)
        self.code = code


def _can_resend_email(profile: Profile) -> None:
    sent_at = profile.email_verification_sent_at
    if not sent_at:
        return
    cooldown = settings.EMAIL_OTP_RESEND_COOLDOWN_SECONDS
    elapsed = (timezone.now() - sent_at).total_seconds()
    if elapsed < cooldown:
        wait = int(cooldown - elapsed)
        raise EmailVerificationError(
            f'Please wait {wait} seconds before requesting another code.',
            code='cooldown',
        )


def issue_email_code(profile: Profile) -> str:
    """Generate 6-digit email code (mobile). Always returns plaintext for email delivery."""
    _can_resend_email(profile)
    code = f'{random.randint(0, 999999):06d}'
    profile.email_otp_hash = make_password(code)
    profile.email_verification_sent_at = timezone.now()
    profile.email_otp_attempts = 0
    profile.save(update_fields=[
        'email_otp_hash', 'email_verification_sent_at', 'email_otp_attempts',
    ])
    if settings.DEBUG:
        logger.warning('DEV email code for %s: %s', profile.user.email, code)
    return code


def verify_email_code(profile: Profile, code: str) -> None:
    raw = (code or '').strip()
    if not raw.isdigit() or len(raw) != 6:
        raise EmailVerificationError('Enter the 6-digit code from your email.', code='invalid_code')

    if not profile.email_otp_hash:
        raise EmailVerificationError('Request a verification code first.', code='no_code')

    expiry = settings.EMAIL_OTP_EXPIRY_MINUTES
    if profile.email_verification_sent_at:
        age = (timezone.now() - profile.email_verification_sent_at).total_seconds()
        if age > expiry * 60:
            raise EmailVerificationError('Code expired. Request a new one.', code='expired')

    if profile.email_otp_attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
        raise EmailVerificationError('Too many attempts. Request a new code.', code='max_attempts')

    if not check_password(raw, profile.email_otp_hash):
        profile.email_otp_attempts += 1
        profile.save(update_fields=['email_otp_attempts'])
        raise EmailVerificationError('Incorrect verification code.', code='invalid_code')

    profile.mark_email_verified()
