from django.utils.text import slugify


def make_slug(base, model, slug_field='slug', instance_pk=None, max_length=50):
    slug = slugify(base)[:max_length] or 'item'
    original = slug
    counter = 1
    while True:
        qs = model.objects.filter(**{slug_field: slug})
        if instance_pk:
            qs = qs.exclude(pk=instance_pk)
        if not qs.exists():
            return slug
        suffix = f'-{counter}'
        slug = f'{original[: max_length - len(suffix)]}{suffix}'
        counter += 1
