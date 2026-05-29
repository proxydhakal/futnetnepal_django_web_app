from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('register/', views.StaffRegisterView.as_view(), name='register'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('', views.DashboardHomeView.as_view(), name='home'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('users/', views.UsersManagementView.as_view(), name='users'),
    path('transactions/', views.TransactionsView.as_view(), name='transactions'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('api/stats/', views.StatsAPIView.as_view(), name='api_stats'),
    path('api/analytics/', views.AnalyticsAPIView.as_view(), name='api_analytics'),
    path('api/activity/', views.ActivityAPIView.as_view(), name='api_activity'),
    path('api/slugify/', views.SlugifyAPIView.as_view(), name='api_slugify'),
    path('api/<str:model_key>/list/', views.ModelListAPIView.as_view(), name='api_list'),
    path('api/<str:model_key>/create/', views.ModelCreateAPIView.as_view(), name='api_create'),
    path('api/<str:model_key>/<str:pk>/', views.ModelDetailAPIView.as_view(), name='api_detail'),
    path('api/<str:model_key>/<str:pk>/update/', views.ModelUpdateAPIView.as_view(), name='api_update'),
    path('api/<str:model_key>/<str:pk>/delete/', views.ModelDeleteAPIView.as_view(), name='api_delete'),
    path('<str:model_key>/', views.ModelListView.as_view(), name='model_list'),
]
