import array
from multiprocessing import context
from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.views import View
from django.contrib import messages
from django.db.models import Count
from django.views.generic import TemplateView,CreateView,ListView
from apps.core.models import Time,Location, Post, Venue
from apps.accounts.models import Profile
from django.db.models import F
from apps.core.forms import UserPostForm, ContactForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.urls import reverse_lazy
from django.views.generic.edit import DeleteView
# Create your views here.

def index(request):
    template_name='core/index.html'
    if request.user.is_authenticated:
        return redirect('/home/')
    else:
        return render(request, template_name)
    


def about(request):
    template_name='core/about.html'
    return render(request, template_name)


def partnerwithus(request):
    template_name='core/partnerwithus.html'
    return render(request, template_name)


class ContactView(View):
    template_name = 'core/contact.html'

    def get(self, request, *args, **kwargs):
        form = ContactForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            contact.save()  
            email = form.cleaned_data['email']
            email_context = {
                'email': email,  
            }
            email_message = render_to_string('email/contact_template.html', email_context)
            email_subject = 'Thank You for Your Message'
            email_from = settings.EMAIL_HOST_USER
            email_to = [email]
            msg = EmailMultiAlternatives(email_subject, email_message, email_from, email_to)
            msg.attach_alternative(email_message, "text/html")
            msg.send()
            messages.success(request, 'Message submitted successfully.')
            return redirect('contact')
        else:
            return render(request, self.template_name, {'form': form})

def review(request):
    template_name='core/review.html'
    return render(request, template_name)


class HomeView(LoginRequiredMixin,View):
    template_name='core/home.html'
    form_class = UserPostForm

    def get(self, request, *args, **kwargs):
        form = UserPostForm()
        context = dict()
        context["form"] = form
        context["posts"] = Post.objects.select_related('author__profile').order_by('-created_at')
        # print(vars(posts.first()))
            
        context["venues"] = Venue.objects.all()
        context["timess"] = Time.objects.all()
        context["locations"] = Location.objects.all()
        context["userprofiledata"]  = Profile.objects.get(user=request.user.pk)
        context["times"] = Time.objects.values('id', 'name').annotate(total=Count('post'))
        return render(request, self.template_name,context)

    def post(self, request, *args, **kwargs):
        form = UserPostForm(request.POST)
        time_value = request.POST.get('time')
        location_value = request.POST.get('location')
        venue_value = request.POST.get('venue')
        context = dict()
        context= {'form':form, 'time_value':time_value, 'location_value':location_value,'venue_value':venue_value}
        context["posts"] = Post.objects.select_related('author__profile').order_by('-created_at')
        # print(vars(posts.first()))
            
        context["venues"] = Venue.objects.all()
        context["timess"] = Time.objects.all()
        context["locations"] = Location.objects.all()
        context["userprofiledata"]  = Profile.objects.get(user=request.user.pk)
        context["times"] = Time.objects.values('id', 'name').annotate(total=Count('post'))

        if form.is_valid():
            post = form.save(commit=False) 
            post.author = request.user 
            post.save()  
            return redirect('/home/')
        else:
            return render(request, self.template_name,context)

class CategoryPostListView(ListView):
    model = Post
    template_name = 'core/post_by_category.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.kwargs.get('pk')
        posts = Post.objects.filter(time__id=query).order_by('-created_at')
        posts = posts.annotate(pimage=models.F('author__profile__profile_image'))
        context["categories"] = posts
        context["userprofiledata"] = Profile.objects.get(user=self.request.user.pk)
        context["times"] = Time.objects.values('id', 'name').annotate(total=Count('post'))
        context["venues"] = Venue.objects.all()
        context["locations"] = Location.objects.all()
        return context



class VenueListView(ListView):
    model =Venue
    template_name = 'core/venuelist.html'

    def get_context_data(self, **kwargs):
        context = super(VenueListView, self).get_context_data(**kwargs)
        context['venues'] = Venue.objects.all()
        return context
    
class PostDeleteView(DeleteView):
    model = Post
    success_url = reverse_lazy('home')
    template_name = 'core/post_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        post = self.get_object()
        result = super().delete(request, *args, **kwargs)
        messages.success(self.request, 'Post deleted successfully.')
        return result  

def get_edit_data(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
        # Create a dictionary with the data to send back as JSON
        data = {
            'location': post.location.id,
            'venue': post.venue.id,
            'date': post.date.strftime('%Y-%m-%d'),
            'time': post.time.id,
            'message': post.message,
        }
        return JsonResponse(data)
    except Post.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)
    

@csrf_exempt  # Only for demonstration, consider using proper CSRF handling
def update_post(request, post_id):
    now = datetime.now()
    formatted_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
    form = UserPostForm(request.POST)
    if request.method == 'POST':
        try:
            post = Post.objects.get(pk=post_id)
            # Update the fields based on the data sent via AJAX
            if post.author_id == request.user.pk:
                post.location_id = request.POST.get('location')
                post.venue_id = request.POST.get('venue')
                post.date = request.POST.get('date')
                post.time_id = request.POST.get('time')
                post.message = request.POST.get('message')
                post.updated_at = formatted_datetime
                post.save()
                return JsonResponse({'success': 'Data updated successfully'})
            else:
                 return JsonResponse({'error': 'Your are not authorized user to update the post!'})
        except Post.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

