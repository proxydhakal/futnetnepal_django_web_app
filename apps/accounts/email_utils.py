import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from futnetnepal.email import base_email_context, resolve_recipients, send_branded_email, site_origin

logger = logging.getLogger(__name__)


def _email_context(user, **extra):
    return base_email_context(
        user=user,
        display_name=user.get_full_name() or user.username,
        **extra,
    )


def send_test_email(to_address):
    """Send a branded SMTP test message (management command / diagnostics)."""
    send_branded_email(
        subject='Futnet Nepal — email test',
        text_template='email/test_email.txt',
        html_template='email/test_email.html',
        context={'smtp_host': settings.EMAIL_HOST},
        to_addresses=[to_address],
    )
    logger.info('Test email sent to %s', to_address)


def send_verification_email_link(user, profile):
    """Web signup: verification link in email."""
    token = profile.ensure_verification_token()
    verify_path = reverse('accounts:verify_email', kwargs={'token': token})
    verify_url = f'{site_origin()}{verify_path}'
    context = _email_context(user, verify_url=verify_url)
    subject = render_to_string('accounts/email/verification_subject.txt', context).strip()
    recipients = send_branded_email(
        subject=subject,
        text_template='accounts/email/verification_email.txt',
        html_template='accounts/email/verification_email.html',
        context=context,
        to_addresses=[user.email],
    )
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
    recipients = send_branded_email(
        subject=subject,
        text_template='accounts/email/verification_code_email.txt',
        html_template='accounts/email/verification_code_email.html',
        context=context,
        to_addresses=[user.email],
    )
    logger.info('Verification code email sent to %s', recipients)
