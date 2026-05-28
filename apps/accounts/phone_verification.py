import random
import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts.models import Profile
from apps.accounts.sms import SmsDeliveryError, send_sms

_PHONE_RE = re.compile(r'^[9][6-8]\d{8}$')


class PhoneVerificationError(Exception):
    def __init__(self, message, code='invalid'):
        super().__init__(message)
        self.code = code


def normalize_phone(raw: str) -> str:
    digits = ''.join(c for c in (raw or '').strip() if c.isdigit())
    if len(digits) == 13 and digits.startswith('977'):
        digits = digits[3:]
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    if not _PHONE_RE.match(digits):
        raise PhoneVerificationError(
            'Enter a valid 10-digit Nepal mobile number (e.g. 9840123456).',
            code='invalid_phone',
        )
    return digits


def _otp_message(code: str) -> str:
    return f'Your Futnet Nepal verification code is {code}. Valid for {settings.PHONE_OTP_EXPIRY_MINUTES} minutes.'


def _can_resend(profile: Profile) -> None:
    sent_at = profile.phone_otp_sent_at
    if not sent_at:
        return
    cooldown = settings.PHONE_OTP_RESEND_COOLDOWN_SECONDS
    elapsed = (timezone.now() - sent_at).total_seconds()
    if elapsed < cooldown:
        wait = int(cooldown - elapsed)
        raise PhoneVerificationError(
            f'Please wait {wait} seconds before requesting another code.',
            code='cooldown',
        )


def issue_phone_otp(profile: Profile, phone: str) -> str:
    """Generate OTP, store hash on profile, send SMS. Returns plaintext OTP in DEBUG only."""
    phone = normalize_phone(phone)
    _can_resend(profile)

    code = f'{random.randint(0, 999999):06d}'
    profile.phone = phone
    profile.phone_verified = False
    profile.phone_otp_hash = make_password(code)
    profile.phone_otp_sent_at = timezone.now()
    profile.phone_otp_attempts = 0
    profile.save(update_fields=[
        'phone', 'phone_verified', 'phone_otp_hash',
        'phone_otp_sent_at', 'phone_otp_attempts',
    ])

    try:
        send_sms(to=phone, text=_otp_message(code))
    except SmsDeliveryError as exc:
        raise PhoneVerificationError(str(exc), code='sms_failed') from exc

    if settings.DEBUG:
        import logging
        logging.getLogger(__name__).warning('DEV phone OTP for %s: %s', phone, code)
    return code if settings.DEBUG else ''


def verify_phone_otp(profile: Profile, phone: str, code: str) -> None:
    phone = normalize_phone(phone)
    raw_code = (code or '').strip()
    if not raw_code.isdigit() or len(raw_code) != 6:
        raise PhoneVerificationError('Enter the 6-digit code from your SMS.', code='invalid_code')

    if profile.phone != phone:
        raise PhoneVerificationError('Phone number does not match.', code='phone_mismatch')

    if not profile.phone_otp_hash:
        raise PhoneVerificationError('Request a verification code first.', code='no_otp')

    expiry = settings.PHONE_OTP_EXPIRY_MINUTES
    if profile.phone_otp_sent_at:
        age = (timezone.now() - profile.phone_otp_sent_at).total_seconds()
        if age > expiry * 60:
            raise PhoneVerificationError('Code expired. Request a new one.', code='expired')

    if profile.phone_otp_attempts >= settings.PHONE_OTP_MAX_ATTEMPTS:
        raise PhoneVerificationError('Too many attempts. Request a new code.', code='max_attempts')

    if not check_password(raw_code, profile.phone_otp_hash):
        profile.phone_otp_attempts += 1
        profile.save(update_fields=['phone_otp_attempts'])
        raise PhoneVerificationError('Incorrect verification code.', code='invalid_code')

    profile.phone_verified = True
    profile.phone_otp_hash = ''
    profile.phone_otp_attempts = 0
    profile.save(update_fields=['phone_verified', 'phone_otp_hash', 'phone_otp_attempts'])


def profile_for_email(email: str) -> Profile:
    email = (email or '').strip().lower()
    if not email:
        raise PhoneVerificationError('Email is required.', code='email_required')
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        raise PhoneVerificationError('No account found for that email.', code='not_found')
    return Profile.objects.get(user=user)


def phone_verification_required(profile: Profile) -> bool:
    return bool(profile.phone) and not profile.phone_verified
