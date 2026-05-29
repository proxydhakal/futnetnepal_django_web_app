# Post primary key → UUIDv7 (time-ordered). Requires empty post graph or fresh DB.

from django.db import migrations, models

from futnetnepal.uuids import time_ordered_uuid


def clear_post_graph(apps, schema_editor):
    """Hard-delete post-related rows so PK type can change."""
    order = (
        'EventChatMessage', 'DirectConversation', 'Notification',
        'PostComment', 'PostReaction', 'PostInterest', 'Post',
    )
    with schema_editor.connection.cursor() as cursor:
        for label in order:
            table = apps.get_model('core', label)._meta.db_table
            cursor.execute(f'DELETE FROM {table}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_soft_delete_timestamps'),
    ]

    operations = [
        migrations.RunPython(clear_post_graph, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='directconversation',
            name='uniq_dm_per_post_pair',
        ),
        migrations.AlterUniqueTogether(
            name='postinterest',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='postreaction',
            unique_together=set(),
        ),
        migrations.RemoveField(model_name='eventchatmessage', name='post'),
        migrations.RemoveField(model_name='directconversation', name='post'),
        migrations.RemoveField(model_name='notification', name='post'),
        migrations.RemoveField(model_name='postcomment', name='post'),
        migrations.RemoveField(model_name='postreaction', name='post'),
        migrations.RemoveField(model_name='postinterest', name='post'),
        migrations.DeleteModel(name='Post'),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=time_ordered_uuid, editable=False, primary_key=True, serialize=False)),
                ('slug', models.SlugField(blank=True, max_length=80, unique=True)),
                ('event_status', models.CharField(
                    choices=[
                        ('open', 'Open'),
                        ('discussing', 'Discussing'),
                        ('confirmed', 'Confirmed'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='open',
                    max_length=20,
                )),
                ('date', models.DateField()),
                ('message', models.TextField()),
                ('author', models.ForeignKey(
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='accounts.user',
                )),
                ('location', models.ForeignKey(
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='core.location',
                )),
                ('time', models.ForeignKey(
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='core.time',
                )),
                ('venue', models.ForeignKey(
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='core.venue',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='postinterest',
            name='post',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='interests',
                to='core.post',
            ),
        ),
        migrations.AddField(
            model_name='postreaction',
            name='post',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='reactions',
                to='core.post',
            ),
        ),
        migrations.AddField(
            model_name='postcomment',
            name='post',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='comments',
                to='core.post',
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='post',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='notifications',
                to='core.post',
            ),
        ),
        migrations.AddField(
            model_name='directconversation',
            name='post',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='direct_conversations',
                to='core.post',
            ),
        ),
        migrations.AddField(
            model_name='eventchatmessage',
            name='post',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='chat_messages',
                to='core.post',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='postinterest',
            unique_together={('post', 'user')},
        ),
        migrations.AlterUniqueTogether(
            name='postreaction',
            unique_together={('post', 'user', 'reaction_type')},
        ),
        migrations.AddConstraint(
            model_name='directconversation',
            constraint=models.UniqueConstraint(
                fields=('post', 'user_a', 'user_b'),
                name='uniq_dm_per_post_pair',
            ),
        ),
    ]
