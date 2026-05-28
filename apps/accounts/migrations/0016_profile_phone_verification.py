from django.db import migrations, models


def mark_existing_phones_verified(apps, schema_editor):
    Profile = apps.get_model('accounts', 'Profile')
    Profile.objects.exclude(phone='').update(phone_verified=True)
    Profile.objects.filter(phone='').update(phone_verified=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_profile_email_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='phone_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='phone_otp_hash',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='profile',
            name='phone_otp_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='phone_otp_attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(mark_existing_phones_verified, migrations.RunPython.noop),
    ]
