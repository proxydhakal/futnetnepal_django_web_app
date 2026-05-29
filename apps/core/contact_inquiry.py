import logging

from django.conf import settings
from django.utils import timezone

from futnetnepal.audit import _valid_audit_user, get_audit_user
from futnetnepal.email import send_branded_email, site_origin

logger = logging.getLogger(__name__)


def _contact_context(contact, **extra):
    return {
        'display_name': contact.fullname,
        'fullname': contact.fullname,
        'email': contact.email,
        'phone': contact.phone,
        'subject': contact.get_subject_display(),
        'message': contact.message,
        'admin_response': contact.admin_response,
        'admin_contacts_url': f'{site_origin()}/iamadmin/core.contact/',
        **extra,
    }


def send_contact_inquiry_received_emails(contact):
    """Notify admin of a new inquiry and send confirmation to the submitter."""
    context = _contact_context(contact)

    admin_recipients = send_branded_email(
        subject=f'New contact inquiry: {contact.get_subject_display()} — {contact.fullname}',
        text_template='email/contact_admin_inquiry.txt',
        html_template='email/contact_admin_inquiry.html',
        context=context,
        to_addresses=[settings.FUTNET_INFO_EMAIL],
    )
    user_recipients = send_branded_email(
        subject='Thank you for contacting Futnet Nepal',
        text_template='email/contact_received_user.txt',
        html_template='email/contact_received_user.html',
        context=context,
        to_addresses=[contact.email],
    )
    logger.info(
        'Contact inquiry emails sent for %s (admin=%s, user=%s)',
        contact.pk,
        admin_recipients,
        user_recipients,
    )


def send_contact_reply_to_user_email(contact):
    """Email the customer when staff save an admin response."""
    context = _contact_context(contact)
    recipients = send_branded_email(
        subject=f'Re: {contact.get_subject_display()} — Futnet Nepal',
        text_template='email/contact_admin_reply_user.txt',
        html_template='email/contact_admin_reply_user.html',
        context=context,
        to_addresses=[contact.email],
    )
    logger.info(
        'Contact reply email sent for inquiry %s (recipients=%s)',
        contact.pk,
        recipients,
    )


def maybe_send_contact_admin_reply(contact, *, previous_response=''):
    """
    After admin saves a response in /iamadmin/, update status metadata and email the user.
    Returns True if a new reply email was sent.
    """
    new_response = (contact.admin_response or '').strip()
    if not new_response or new_response == (previous_response or '').strip():
        return False

    user = get_audit_user()
    update_fields = ['status', 'responded_at', 'admin_response', 'updated_at']
    contact.status = contact.STATUS_RESPONDED
    contact.responded_at = timezone.now()
    if _valid_audit_user(user):
        contact.responded_by = user
        update_fields.append('responded_by')

    contact.save(update_fields=update_fields)
    send_contact_reply_to_user_email(contact)
    return True
