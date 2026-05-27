from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_backfill_direct_conversations'),
    ]

    operations = [
        migrations.AddField(
            model_name='venuebooking',
            name='preferred_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
