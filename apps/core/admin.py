from django.contrib import admin
from apps.core.models import Location, Venue, Time, Post

# Register your models here.
admin.site.register(Location)
admin.site.register(Venue)
admin.site.register(Time)
admin.site.register(Post)