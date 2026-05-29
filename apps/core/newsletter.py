import logging

from django.conf import settings

from futnetnepal.email import send_branded_email

logger = logging.getLogger(__name__)


def send_newsletter_subscription_emails(subscription):
    """Notify the subscriber and Futnet admin (info@futnetnepal.com)."""
    context = {
        'name': subscription.name,
        'email': subscription.email,
    }

    subscriber_recipients = send_branded_email(
        subject='Welcome to the Futnet Nepal newsletter',
        text_template='email/newsletter_subscriber.txt',
        html_template='email/newsletter_subscriber.html',
        context=context,
        to_addresses=[subscription.email],
    )
    admin_recipients = send_branded_email(
        subject=f'New newsletter subscriber: {subscription.name}',
        text_template='email/newsletter_admin.txt',
        html_template='email/newsletter_admin.html',
        context=context,
        to_addresses=[settings.FUTNET_INFO_EMAIL],
    )
    logger.info(
        'Newsletter emails sent for %s (subscriber=%s, admin=%s)',
        subscription.email,
        subscriber_recipients,
        admin_recipients,
    )
