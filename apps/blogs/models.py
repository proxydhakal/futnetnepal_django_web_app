from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField

from futnetnepal.models import TimestampedSoftDeleteModel


class Category(TimestampedSoftDeleteModel):
    title = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.title


class Tag(TimestampedSoftDeleteModel):
    t_name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['t_name']
        verbose_name_plural = 'tags'

    def __str__(self):
        return self.t_name


class Blog(TimestampedSoftDeleteModel):
    title = models.CharField(max_length=255)
    content = RichTextUploadingField()
    count = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    cover_image = models.ImageField(upload_to='media/blog', null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField(Tag)
    slug = models.SlugField(null=True, max_length=255, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        category_slug = self.category.title if self.category else 'general'
        return reverse(
            'blog_detail',
            kwargs={'slug': self.slug, 'category': category_slug},
        )
