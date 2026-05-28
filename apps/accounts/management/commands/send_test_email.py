from django.core.management.base import BaseCommand, CommandError

from apps.accounts.email_utils import send_test_email


class Command(BaseCommand):
    help = 'Send a test email via configured SMTP (verify delivery).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            default='proxydhakal@gmail.com',
            help='Recipient address (default: proxydhakal@gmail.com)',
        )

    def handle(self, *args, **options):
        to = (options['to'] or '').strip()
        if not to:
            raise CommandError('--to is required')

        from django.conf import settings

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError(
                'EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must be set in .env'
            )

        self.stdout.write(
            f'Sending test email to {to} via {settings.EMAIL_HOST} '
            f'as {settings.DEFAULT_FROM_EMAIL} …'
        )
        try:
            send_test_email(to)
        except Exception as exc:
            raise CommandError(f'SMTP failed: {exc}') from exc

        self.stdout.write(self.style.SUCCESS(f'Test email sent to {to}'))
