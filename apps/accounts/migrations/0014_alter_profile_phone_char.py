from django.db import migrations, models


def copy_phone_to_str(apps, schema_editor):
    Profile = apps.get_model('accounts', 'Profile')
    for profile in Profile.objects.all():
        old = profile.phone
        profile.phone_str = str(old)[:10] if old is not None else ''
        profile.save(update_fields=['phone_str'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_alter_profile_phone_bigint'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='phone_str',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
        migrations.RunPython(copy_phone_to_str, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='profile',
            name='phone',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='phone_str',
            new_name='phone',
        ),
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(
                blank=True,
                default='',
                help_text='10-digit contact number',
                max_length=10,
            ),
        ),
    ]
