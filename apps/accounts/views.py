from multiprocessing import context
from django.shortcuts import render,redirect,get_object_or_404,HttpResponse
from django.views import View
from apps.accounts.forms import UserRegisterForm
from apps.accounts.models import Profile
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from apps.core.models import Post
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin

def success(request):
    template_name='accounts/success.html'
    return render(request, template_name)

class SignUpView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return render(request,'accounts/register_user.html')
        else:
            template_name='accounts/register.html'
            form = UserRegisterForm()
            return render(request,template_name,{'form':form})

    def post(self, request, *args, **kwargs):
        form = UserRegisterForm(request.POST)
        template_name='accounts/login.html'
        if form.is_valid():
            user =form.save(commit=False)
            raw_password = form.cleaned_data['password']
            username = form.cleaned_data['username']
            user.set_password(raw_password)
            user.save()
            messages.success(request, f'Account created for {username}!')
            return redirect('/accounts/login')

        else:
            return render(request, 'accounts/register.html', {'form':form})

class UserProfileView(LoginRequiredMixin, View):
    template_name = 'account/profile.html'

    def get(self, request, *args, **kwargs):
        userprofiledata  = Profile.objects.filter(user=request.user.pk).first()
        print(userprofiledata.profile_image.url)
        posts = Post.objects.filter(author=request.user).order_by('-created_at')
        context = {'posts': posts, 'userprofiledata':userprofiledata}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Handle POST requests here
        # You can add logic to process data from a submitted form, for example, creating a new post
        # After processing the POST data, you can redirect to the user's profile page or render a response
        # Example:
        # new_post = Post(author=request.user, content=request.POST['post_content'])
        # new_post.save()
        # return redirect('profile')  # Redirect to the user's profile page
        return self.get(request, *args, **kwargs) 


    