from django.db import migrations, models
from django.utils.text import slugify


def _unique_slug(base, existing_slugs, max_length=80):
    slug = slugify(base)[:max_length] or 'item'
    original = slug
    counter = 1
    while slug in existing_slugs:
        suffix = f'-{counter}'
        slug = f'{original[: max_length - len(suffix)]}{suffix}'
        counter += 1
    existing_slugs.add(slug)
    return slug


def populate_slugs(apps, schema_editor):
    Time = apps.get_model('core', 'Time')
    Venue = apps.get_model('core', 'Venue')
    Post = apps.get_model('core', 'Post')

    used = set()
    for obj in Time.objects.all():
        obj.slug = _unique_slug(obj.name, used, 80)
        obj.save(update_fields=['slug'])

    used = set()
    for obj in Venue.objects.all():
        obj.slug = _unique_slug(obj.name, used, 60)
        obj.save(update_fields=['slug'])

    used = set()
    for obj in Post.objects.all():
        base = (obj.message or 'event')[:50]
        obj.slug = _unique_slug(base, used, 80)
        obj.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_alter_eventchatmessage_id_alter_notification_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='time',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name='venue',
            name='slug',
            field=models.SlugField(blank=True, max_length=60, null=True),
        ),
        migrations.AddField(
            model_name='post',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, null=True),
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='time',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, unique=True),
        ),
        migrations.AlterField(
            model_name='venue',
            name='slug',
            field=models.SlugField(blank=True, max_length=60, unique=True),
        ),
        migrations.AlterField(
            model_name='post',
            name='slug',
            field=models.SlugField(blank=True, max_length=80, unique=True),
        ),
    ]
