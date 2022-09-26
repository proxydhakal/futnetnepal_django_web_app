from django.urls import path
from apps.core import views
from apps.accounts.views import UserProfileView
urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('partnerwithus', views.partnerwithus, name='partnerwithus'),
    path('contact', views.contact, name='contact'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('review', views.review, name='review'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('home/<int:pk>', views.CategoryPostListView.as_view(), name='post-cat'),
]