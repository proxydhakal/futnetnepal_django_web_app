from django.db import migrations


def backfill(apps, schema_editor):
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
        ('core', '0015_direct_conversation_dm'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
