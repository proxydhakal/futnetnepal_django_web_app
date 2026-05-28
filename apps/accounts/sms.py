import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

AAKASH_SMS_SEND_URL = 'https://sms.aakashsms.com/sms/v3/send'


class SmsDeliveryError(Exception):
    pass


def send_sms(*, to: str, text: str) -> None:
    """
    Send SMS via Aakash SMS (POST). `to` must be comma-separated 10-digit numbers.
  """
    token = getattr(settings, 'AAKASH_SMS_AUTH_TOKEN', '') or ''
    if not token:
        if settings.DEBUG:
            logger.warning('AAKASH_SMS_AUTH_TOKEN not set; SMS not sent. text=%s to=%s', text, to)
            return
        raise SmsDeliveryError('SMS is not configured.')

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
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8', errors='replace')
    except (HTTPError, URLError) as exc:
        logger.exception('Aakash SMS request failed')
        raise SmsDeliveryError('Could not reach SMS gateway.') from exc

    try:
        data = json.loads(body) if body.strip().startswith('{') else {}
    except json.JSONDecodeError:
        data = {}

    if data.get('error') is True or data.get('success') is False:
        message = data.get('message') or body or 'SMS gateway rejected the request.'
        raise SmsDeliveryError(str(message))

    logger.info('SMS sent to %s', to)
