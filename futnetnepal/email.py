"""Shared HTML email branding and send helper."""

import logging

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def site_origin():
    return getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')


def logo_url():
    path = staticfiles_storage.url('images/logo.png')
    if path.startswith('http'):
        return path
    return f'{site_origin()}{path}'


def base_email_context(**extra):
    return {
        'site_name': 'Futnet Nepal',
        'site_url': site_origin(),
        'logo_url': logo_url(),
        'info_email': getattr(settings, 'FUTNET_INFO_EMAIL', 'info@futnetnepal.com'),
        'copyright_year': timezone.now().year,
        **extra,
    }


def resolve_recipients(*addresses):
    """Return recipient list; optional EMAIL_OVERRIDE_RECIPIENT redirects all mail."""
    override = getattr(settings, 'EMAIL_OVERRIDE_RECIPIENT', '') or ''
    if override:
        return [override]
    return [a for a in addresses if a]


def send_branded_email(*, subject, text_template, html_template, context, to_addresses, from_email=None):
    """Send multipart email (plain text + HTML) using branded templates."""
    full_context = base_email_context(**context)
    text_body = render_to_string(text_template, full_context)
    html_body = render_to_string(html_template, full_context)
    recipients = resolve_recipients(*to_addresses)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
    return recipients
