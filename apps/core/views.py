import array
from multiprocessing import context
from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.views import View
from django.contrib import messages
from django.db.models import Count
from django.views.generic import TemplateView,CreateView,ListView
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
        form = UserPostForm()
        context = dict()
        context={'form':form}
        context["posts"] = Post.objects.raw('''SELECT core_post.* ,accounts_profile.profile_image as pimage
                                                FROM core_post        
                                                JOIN accounts_profile        
                                                ON core_post.author_id = accounts_profile.user_id
                                                ORDER BY core_post.created_at DESC''')       
        context["times"] = Time.objects.all()
        context["venues"] = Venue.objects.all()
        context["locations"] = Location.objects.all()
        context["times"] = Time.objects.raw('''SELECT core_time.id, core_time.name as Name, COUNT(core_post.time_id) as Total
                                                FROM core_time
                                                JOIN core_post ON core_time.id = core_post.time_id
                                                GROUP BY core_time.id, core_time.name''')
        return render(request, self.template_name,context)

    def post(self, request, *args, **kwargs):
        form = UserPostForm(request.POST or None)
        if form.is_valid():
            location = form.cleaned_data.get("location")
            venue = form.cleaned_data.get("venue")
            date = form.cleaned_data.get("date")
            time = form.cleaned_data.get("time")
            message = form.cleaned_data.get("message")
            data ={'location':location, 'venue':venue, 'date':date,'time':time,'message': message}
            data =form.save(commit=False)
            data.author =self.request.user
            data.save()
            messages.success(request, f'Event created successfully!')
            return HttpResponseRedirect('/home/')
        else:
            messages.error(request, 'Error creating post!')
            form = UserPostForm()
            return render(request, self.template_name,context={'form':form})

class CategoryPostListView(ListView):
    model =Post
    template_name = 'core/post_by_category.html'

    def get_context_data(self, **kwargs):
        context = super(CategoryPostListView, self).get_context_data(**kwargs)
        query = self.kwargs.get('pk')
        context["categories"] = Post.objects.raw('''SELECT core_post.* ,accounts_profile.profile_image as pimage
                                                    FROM core_post        
                                                    JOIN accounts_profile        
                                                    ON core_post.author_id = accounts_profile.user_id
                                                    Where time_id = %s
                                                    ORDER BY core_post.created_at DESC
                                                    ''' , [query])
        context["times"] = Time.objects.raw('''SELECT core_time.id,core_time.name as Name,COUNT(core_post.time_id) as Total
                                                FROM core_time         
                                                JOIN core_post        
                                                ON core_time.id = core_post.time_id
                                                GROUP BY core_time.name''')
        return context


class VenueListView(ListView):
    model =Venue
    template_name = 'core/venuelist.html'

    def get_context_data(self, **kwargs):
        context = super(VenueListView, self).get_context_data(**kwargs)
        context['venues'] = Venue.objects.all()
        return context