import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

AAKASH_SMS_SEND_URL = 'https://sms.aakashsms.com/sms/v3/send'

# Shown to end users only — never expose gateway balance/auth details.
USER_SMS_SEND_FAILED = (
    'Could not send the verification code. Please try again in a few minutes.'
)
USER_SMS_UNAVAILABLE = (
    'SMS verification is temporarily unavailable. Please try again later.'
)


class SmsDeliveryError(Exception):
    """Raised when SMS cannot be sent; message is safe to show to users."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def _mask_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) <= 4:
        return '****'
    return f'{digits[:2]}****{digits[-2:]}'


def send_sms(*, to: str, text: str) -> None:
    """
    Send SMS via Aakash SMS (POST). `to` must be comma-separated 10-digit numbers.
    Logs full API responses; only generic errors are raised for callers to show users.
    """
    token = getattr(settings, 'AAKASH_SMS_AUTH_TOKEN', '') or ''
    masked = _mask_phone(to)
    if not token:
        if settings.DEBUG:
            logger.warning(
                'AAKASH_SMS_AUTH_TOKEN not set; SMS not sent (dev). to=%s',
                masked,
            )
            return
        logger.error('AAKASH_SMS_AUTH_TOKEN not set; cannot send SMS to=%s', masked)
        raise SmsDeliveryError(USER_SMS_UNAVAILABLE)

    payload = urlencode({
        'auth_token': token,
        'to': to,
        'text': text,
    }).encode('utf-8')
    req = Request(
        AAKASH_SMS_SEND_URL,
        data=payload,
        method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    body = ''
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8', errors='replace')
    except HTTPError as exc:
        try:
            body = exc.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''
        logger.error(
            'Aakash SMS HTTP error for to=%s status=%s body=%s',
            masked,
            exc.code,
            body or exc.reason,
            exc_info=True,
        )
        raise SmsDeliveryError(USER_SMS_SEND_FAILED) from exc
    except URLError as exc:
        logger.exception('Aakash SMS network error for to=%s', masked)
        raise SmsDeliveryError(USER_SMS_SEND_FAILED) from exc

    try:
        data = json.loads(body) if body.strip().startswith('{') else {}
    except json.JSONDecodeError:
        logger.error(
            'Aakash SMS non-JSON response for to=%s body=%r',
            masked,
            body[:500],
        )
        raise SmsDeliveryError(USER_SMS_SEND_FAILED)

    if data.get('error') is True or data.get('success') is False:
        api_message = data.get('message') or data.get('msg') or body or 'unknown'
        logger.error(
            'Aakash SMS API rejected request for to=%s: %s | response=%s',
            masked,
            api_message,
            data,
        )
        raise SmsDeliveryError(USER_SMS_SEND_FAILED)

    logger.info('Aakash SMS accepted for to=%s response=%s', masked, data or body[:200])
