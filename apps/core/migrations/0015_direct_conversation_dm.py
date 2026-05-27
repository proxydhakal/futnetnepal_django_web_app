# Generated manually for person-to-person messaging

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _create_dms_for_interests(apps, schema_editor):
    PostInterest = apps.get_model('core', 'PostInterest')
    DirectConversation = apps.get_model('core', 'DirectConversation')
    for pi in PostInterest.objects.select_related('post').iterator():
        post = pi.post
        if not post.author_id or pi.user_id == post.author_id:
            continue
        a_id, b_id = sorted([pi.user_id, post.author_id])
        DirectConversation.objects.get_or_create(
            post_id=post.id, user_a_id=a_id, user_b_id=b_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_event_chat_messenger'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direct_conversations', to='core.post')),
                ('user_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dm_conversations_as_a', to=settings.AUTH_USER_MODEL)),
                ('user_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dm_conversations_as_b', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='directconversation',
            constraint=models.UniqueConstraint(fields=('post', 'user_a', 'user_b'), name='uniq_dm_per_post_pair'),
        ),
        migrations.AddField(
            model_name='eventchatmessage',
            name='conversation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='core.directconversation'),
        ),
        migrations.RunPython(_create_dms_for_interests, migrations.RunPython.noop),
    ]
