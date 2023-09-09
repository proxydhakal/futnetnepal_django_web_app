from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from apps.accounts.views import SignUpView,UserProfileView,EditProfile
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [

    path('login/', auth_views.LoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(template_name='accounts/logout.html'), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('edit/<str:username>/', EditProfile.as_view(), name='updateprofile'),
    path('signup/', SignUpView.as_view(), name='signup'),
]