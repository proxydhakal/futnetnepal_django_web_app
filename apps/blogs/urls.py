from django.urls import path

from apps.blogs.views import (
    BlogDetail,
    BlogLegacyRedirectView,
    BlogList,
    CategoryBlogListView,
    CategoryLegacyRedirectView,
)

urlpatterns = [
    path('', BlogList.as_view(), name='blog'),
    path('category/<int:category_id>/', CategoryBlogListView.as_view(), name='blog-cat'),
    path('category/<str:category>/', CategoryLegacyRedirectView.as_view(), name='blog-cat-legacy'),
    path('<slug:slug>/', BlogDetail.as_view(), name='blog_detail'),
    # Old URLs: /blog/Community%20Updates/post-slug/ → /blog/post-slug/
    path(
        '<str:category>/<slug:slug>/',
        BlogLegacyRedirectView.as_view(),
        name='blog_detail_legacy',
    ),
]
