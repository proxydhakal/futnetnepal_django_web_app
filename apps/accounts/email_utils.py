import logging

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _site_origin():
    return getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')


def _logo_url():
    path = staticfiles_storage.url('images/logo.png')
    if path.startswith('http'):
        return path
    return f'{_site_origin()}{path}'


def _email_context(user, **extra):
    return {
        'user': user,
        'site_name': 'Futnet Nepal',
        'site_url': _site_origin(),
        'logo_url': _logo_url(),
        'display_name': user.get_full_name() or user.username,
        **extra,
    }


def resolve_recipients(*addresses):
    """Return recipient list; optional EMAIL_OVERRIDE_RECIPIENT redirects all mail."""
    override = getattr(settings, 'EMAIL_OVERRIDE_RECIPIENT', '') or ''
    if override:
        return [override]
    return [a for a in addresses if a]


def send_test_email(to_address):
    """Send a simple SMTP test message (management command / diagnostics)."""
    subject = 'Futnet Nepal — email test'
    body = (
        f'This is an automated test from Futnet Nepal.\n\n'
        f'SMTP host: {settings.EMAIL_HOST}\n'
        f'From: {settings.DEFAULT_FROM_EMAIL}\n'
        f'Site: {_site_origin()}\n'
    )
    sent = send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [to_address],
        fail_silently=False,
    )
    logger.info('Test email sent to %s (count=%s)', to_address, sent)
    return sent


def send_verification_email_link(user, profile):
    """Web signup: verification link in email."""
    token = profile.ensure_verification_token()
    verify_path = reverse('accounts:verify_email', kwargs={'token': token})
    verify_url = f'{_site_origin()}{verify_path}'
    context = _email_context(user, verify_url=verify_url)
    subject = render_to_string('accounts/email/verification_subject.txt', context).strip()
    text_body = render_to_string('accounts/email/verification_email.txt', context)
    html_body = render_to_string('accounts/email/verification_email.html', context)
    recipients = resolve_recipients(user.email)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
    logger.info('Verification link email sent to %s', recipients)


def send_verification_email(user, profile):
    """Backward-compatible alias for web link emails."""
    send_verification_email_link(user, profile)


def send_verification_email_code(user, profile, code: str):
    """Mobile signup: 6-digit code in email (no link)."""
    context = _email_context(
        user,
        verification_code=code,
        expiry_minutes=settings.EMAIL_OTP_EXPIRY_MINUTES,
    )
    subject = render_to_string('accounts/email/verification_code_subject.txt', context).strip()
    text_body = render_to_string('accounts/email/verification_code_email.txt', context)
    html_body = render_to_string('accounts/email/verification_code_email.html', context)
    recipients = resolve_recipients(user.email)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
    logger.info('Verification code email sent to %s', recipients)
