import logging

from django.conf import settings

from futnetnepal.email import send_branded_email, site_origin

logger = logging.getLogger(__name__)


def send_new_review_admin_email(review):
    """Notify Futnet admin about a new user review pending approval."""
    context = {
        'name': review.name,
        'email': review.email,
        'rating': review.rating,
        'message': review.message,
        'admin_reviews_url': f'{site_origin()}/iamadmin/core.userreview/',
    }
    admin_recipients = send_branded_email(
        subject=f'New user review from {review.name} ({review.rating}/5)',
        text_template='email/review_admin.txt',
        html_template='email/review_admin.html',
        context=context,
        to_addresses=[settings.FUTNET_INFO_EMAIL],
    )
    logger.info(
        'Review admin email sent for review %s (recipients=%s)',
        review.pk,
        admin_recipients,
    )
