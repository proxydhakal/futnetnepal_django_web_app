from django.shortcuts import render
from django.views.generic import TemplateView,CreateView
from apps.core.models import Time,Location, Post, Venue
# Create your views here.
def index(request):
    if request.user.is_authenticated:
        template_name='core/home.html'
    else:
        template_name='core/index.html'
    context= {
        'posts': Post.objects.filter().order_by('-created_at'),
        'times': Time.objects.all(),
        'venues': Venue.objects.all()
    }
    return render(request, template_name, context)


def about(request):
    template_name='core/about.html'
    return render(request, template_name)


def partnerwithus(request):
    template_name='core/partnerwithus.html'
    return render(request, template_name)


def contact(request):
    template_name='core/contact.html'
    return render(request, template_name)

def review(request):
    template_name='core/review.html'
    return render(request, template_name)

class HomeView(TemplateView):
    model = Post
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["posts"] = Post.objects.filter().order_by('-created_at')       
        context["times"] = Time.objects.all()
        context["venues"] = Venue.objects.all()
        return context