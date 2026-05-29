# Soft delete + missing timestamps

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_venuebooking_preferred_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='location',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='location', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='location', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='venue',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='venue',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='venue', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='venue', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='time',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='time',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='time', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='time', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='post', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='post', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='venuebooking', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='venuebooking', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='venuebooking',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='postinterest', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='postinterest', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='postinterest',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='postreaction', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='postreaction', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='postreaction',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='postcomment', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='postcomment', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='postcomment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='notification', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='notification', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='notification',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='directconversation', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='directconversation', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='eventchatmessage', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='eventchatmessage', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='eventchatmessage',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='contact', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='contact', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
    ]
