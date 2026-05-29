from django.db.models.signals import post_save
from django.dispatch import receiver

from futnetnepal.audit import _valid_audit_user, audit_user, get_audit_user

from apps.accounts.models import Profile, User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    with audit_user(instance):
        Profile.objects.get_or_create(user=instance)
    if not instance.created_by_id:
        audit = get_audit_user()
        creator_id = audit.pk if _valid_audit_user(audit) else instance.pk
        User.objects.filter(pk=instance.pk).update(created_by_id=creator_id)
        instance.created_by_id = creator_id
