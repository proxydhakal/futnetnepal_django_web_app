from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


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


def send_verification_email_link(user, profile):
    """Web signup: verification link in email."""
    token = profile.ensure_verification_token()
    verify_path = reverse('accounts:verify_email', kwargs={'token': token})
    verify_url = f'{_site_origin()}{verify_path}'
    context = _email_context(user, verify_url=verify_url)
    subject = render_to_string('accounts/email/verification_subject.txt', context).strip()
    text_body = render_to_string('accounts/email/verification_email.txt', context)
    html_body = render_to_string('accounts/email/verification_email.html', context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)


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
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
