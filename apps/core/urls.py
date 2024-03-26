from django.urls import path
from apps.core import views
from apps.accounts.views import UserProfileView
urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('partnerwithus', views.partnerwithus, name='partnerwithus'),
    path('contact', views.ContactView.as_view(), name='contact'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('review', views.review, name='review'),
    path('venuelist/', views.VenueListView.as_view(), name='venuelist'),
    path('home/<int:pk>', views.CategoryPostListView.as_view(), name='post-cat'),
    path('get_edit_data/<int:post_id>/', views.get_edit_data, name='get_edit_data'),
    path('update_post/<int:post_id>/', views.update_post, name='update_post'),
    path('delete_post/<int:pk>/', views.PostDeleteView.as_view(), name='delete_post'),
    
]