from django.contrib import admin
from apps.blogs.models import Category, Tag, Blog

# Register your models here.
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Blog)
