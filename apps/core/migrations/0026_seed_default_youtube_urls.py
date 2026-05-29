from django.db import migrations

DEFAULT_URL = 'https://www.youtube.com/watch?v=_lHve-9EUK0'


def seed_youtube_urls(apps, schema_editor):
    SiteContentSettings = apps.get_model('core', 'SiteContentSettings')
    SiteContentSettings.objects.update_or_create(
        pk=1,
        defaults={
            'about_youtube_url': DEFAULT_URL,
            'home_youtube_url': DEFAULT_URL,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_site_content_settings'),
    ]

    operations = [
        migrations.RunPython(seed_youtube_urls, migrations.RunPython.noop),
    ]
