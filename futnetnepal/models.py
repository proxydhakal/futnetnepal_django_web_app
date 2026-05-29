"""Shared model mixins: soft delete, timestamps, and audit users."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from futnetnepal.audit import _valid_audit_user, get_audit_user


def _extend_update_fields(kwargs, *names):
    update_fields = kwargs.get('update_fields')
    if update_fields is None:
        return kwargs
    extended = list(update_fields)
    for name in names:
        if name not in extended:
            extended.append(name)
    kwargs['update_fields'] = extended
    return kwargs


class AuditUserMixin(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated',
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_deleted',
    )

    class Meta:
        abstract = True

    def _apply_audit_on_save(self, **kwargs):
        user = get_audit_user()
        if not _valid_audit_user(user):
            return kwargs
        if self._state.adding and not self.created_by_id:
            self.created_by = user
            kwargs = _extend_update_fields(kwargs, 'created_by')
        elif not self._state.adding:
            self.updated_by = user
            kwargs = _extend_update_fields(kwargs, 'updated_by')
        return kwargs

    def _audit_delete_user_fields(self):
        user = get_audit_user()
        if _valid_audit_user(user):
            self.deleted_by = user
            return ['deleted_by']
        return []


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        updates = {
            'is_deleted': True,
            'deleted_at': timezone.now(),
        }
        if hasattr(self.model, 'deleted_by_id'):
            user = get_audit_user()
            if _valid_audit_user(user):
                updates['deleted_by_id'] = user.pk
        return super().update(**updates)

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        update_fields = ['is_deleted', 'deleted_at']
        if hasattr(self, '_audit_delete_user_fields'):
            update_fields.extend(self._audit_delete_user_fields())
        self.save(update_fields=update_fields)

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        update_fields = ['is_deleted', 'deleted_at']
        if hasattr(self, 'deleted_by_id'):
            self.deleted_by = None
            update_fields.append('deleted_by')
        self.save(update_fields=update_fields)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TimestampedSoftDeleteModel(TimestampedModel, SoftDeleteModel, AuditUserMixin):
    """Timestamps, soft delete, and created_by / updated_by / deleted_by."""

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        kwargs = self._apply_audit_on_save(**kwargs)
        super().save(*args, **kwargs)
