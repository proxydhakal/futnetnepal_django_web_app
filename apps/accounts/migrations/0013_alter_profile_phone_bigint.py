import re

from django.db import migrations, models


def convert_phone_to_bigint(apps, schema_editor):
    Profile = apps.get_model('accounts', 'Profile')
    for profile in Profile.objects.exclude(phone__isnull=True).exclude(phone=''):
        raw = str(profile.phone)
        digits = re.sub(r'\D', '', raw)
        if digits:
            profile.phone = int(digits)
            profile.save(update_fields=['phone'])
        else:
            profile.phone = None
            profile.save(update_fields=['phone'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_alter_profile_phone'),
    ]

    operations = [
        migrations.RunPython(convert_phone_to_bigint, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.BigIntegerField(blank=True, help_text='Contact phone number', null=True),
        ),
    ]
