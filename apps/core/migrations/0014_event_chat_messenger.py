from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0013_time_venue_post_slugs'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='event_status',
            field=models.CharField(
                choices=[
                    ('open', 'Open'),
                    ('discussing', 'Discussing'),
                    ('confirmed', 'Confirmed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='open',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='postinterest',
            name='participation_status',
            field=models.CharField(
                choices=[
                    ('interested', 'Interested'),
                    ('confirmed', 'Confirmed'),
                    ('declined', 'Declined'),
                ],
                default='interested',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='eventchatmessage',
            name='message_type',
            field=models.CharField(
                choices=[
                    ('text', 'Text'),
                    ('system', 'System'),
                    ('attendance', 'Attendance'),
                    ('event_confirmed', 'Event confirmed'),
                ],
                default='text',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='eventchatmessage',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='event_chat_messages',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
