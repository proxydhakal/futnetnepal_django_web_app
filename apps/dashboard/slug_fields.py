"""Slug fields in /iamadmin/ CRUD: source mapping and generation."""

from django.db import models

from apps.core.slugs import make_slug

SLUG_FIELD = 'slug'
SOURCE_FIELD_PRIORITY = ('title', 'name', 'message')


def get_slug_source_field(model) -> str | None:
    names = {f.name for f in model._meta.fields if getattr(f, 'concrete', False)}
    if SLUG_FIELD not in names:
        return None
    for candidate in SOURCE_FIELD_PRIORITY:
        if candidate in names:
            return candidate
    return None


def slug_max_length(model) -> int:
    field = model._meta.get_field(SLUG_FIELD)
    return getattr(field, 'max_length', None) or 50


def generate_unique_slug(text: str, model, *, instance_pk=None) -> str:
    base = (text or '').strip() or 'item'
    return make_slug(base, model, instance_pk=instance_pk, max_length=slug_max_length(model))


def apply_auto_slug_to_payload(meta, payload: dict, instance=None) -> dict:
    """Ensure slug is set from the source field before model form validation."""
    source = get_slug_source_field(meta.model)
    if not source:
        return payload
    base = (payload.get(source) or '').strip()
    if not base and instance is not None:
        base = (getattr(instance, source, None) or '').strip()
    if not base:
        return payload
    pk = instance.pk if instance is not None else payload.get('id')
    payload[SLUG_FIELD] = generate_unique_slug(base, meta.model, instance_pk=pk)
    return payload
