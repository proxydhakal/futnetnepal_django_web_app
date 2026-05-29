from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.blogs.models import Blog, Category


class BlogList(ListView):
    model = Blog
    ordering = ['-created_at']
    context_object_name = 'list_blogs'
    template_name = 'blogs/blog.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class BlogDetail(DetailView):
    model = Blog
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    template_name = 'blogs/singleblog.html'
    context_object_name = 'single_blogs'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.count = self.object.count + 1
        context['blogs'] = Blog.objects.order_by('-count')[:2]
        context['categories'] = Category.objects.all()
        self.object.save(update_fields=['count'])
        if self.object.category_id:
            context['category_id'] = self.object.category_id
        return context


class CategoryBlogListView(ListView):
    model = Blog
    template_name = 'blogs/blog_by_category.html'
    context_object_name = 'list_blogs'
    ordering = ['-created_at']

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        return Blog.objects.filter(category_id=category_id).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = get_object_or_404(Category, pk=self.kwargs.get('category_id'))
        context['category'] = category
        context['category_name'] = category.title
        context['category_id'] = category.pk
        context['categories'] = Category.objects.all()
        return context


class BlogLegacyRedirectView(View):
    """Permanent redirect from old /blog/<category>/<slug>/ URLs."""

    def get(self, request, category, slug):
        return redirect('blog_detail', slug=slug, permanent=True)


class CategoryLegacyRedirectView(View):
    """Permanent redirect from old /blog/category/<title>/ URLs."""

    def get(self, request, category):
        cat = Category.objects.filter(title__iexact=category).first()
        if cat:
            return redirect('blog-cat', category_id=cat.pk, permanent=True)
        return redirect('blog')
