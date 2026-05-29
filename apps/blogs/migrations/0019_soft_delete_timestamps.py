# Soft delete + timestamps for blog models

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0007_auto_20221011_0814'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='category',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='category', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='category', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(
            model_name='tag',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tag',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(model_name='tag', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='tag', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='blog', name='is_deleted', field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name='blog', name='deleted_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
    ]
