from django.urls import path
from apps.core import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('partnerwithus', views.partnerwithus, name='partnerwithus'),
    path('contact', views.contact, name='contact'),
    path('review', views.review, name='review'),
]