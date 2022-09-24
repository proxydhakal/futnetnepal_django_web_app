import array
from multiprocessing import context
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views import View
from django.contrib import messages
from django.views.generic import TemplateView,CreateView
from apps.core.models import Time,Location, Post, Venue
from apps.core.forms import UserPostForm
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
def index(request):
    template_name='core/index.html'
    return render(request, template_name)


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


class HomeView(LoginRequiredMixin,View):
    template_name='core/home.html'
    form_class = UserPostForm

    def get(self, request, *args, **kwargs):
        context = dict()
        context["posts"] = Post.objects.filter().order_by('-created_at')       
        context["times"] = Time.objects.all()
        context["venues"] = Venue.objects.all()
        context["locations"] = Location.objects.all()
        return render(request, self.template_name,context)

    def post(self, request, *args, **kwargs):
        form = UserPostForm(request.POST)
        if form.is_valid():
            data =form.save(commit=False)
            data.author =self.request.user
            data.save()
            messages.success(request, f'Event created successfully!')
            return HttpResponseRedirect('/')
        else:
            form = UserPostForm()
        return render(request, self.template_name,{'form':form})