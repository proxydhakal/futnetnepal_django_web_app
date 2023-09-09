from multiprocessing import context
from django.shortcuts import render,redirect,get_object_or_404,HttpResponse
from django.views import View
from apps.accounts.forms import UserRegisterForm, CombinedProfileUpdateForm,UserProfileUpdateForm
from apps.accounts.models import Profile
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from apps.core.models import Post
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView,DetailView
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
        userprofiledata  = Profile.objects.get(user=request.user.pk)
        posts = Post.objects.filter(author=request.user).order_by('-created_at')
        context = {'posts': posts, 'userprofiledata':userprofiledata}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs) 


# class EditProfile(LoginRequiredMixin,View):
#     template_name = 'account/edit_profile.html' 

#     def get(self, request, *args, **kwargs):
#         userprofiledata  = Profile.objects.get(user=request.user.pk)
#         context = {'userprofiledata':userprofiledata}
#         return render(request, self.template_name, context)
    
class EditProfile(LoginRequiredMixin, View):
    template_name = 'account/edit_profile.html'

    def get(self, request, *args, **kwargs):
        user_profile = Profile.objects.get(user=request.user)
        user_data = {
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
        form = UserProfileUpdateForm(instance=user_profile, initial=user_data)
        context = {'form': form,'userprofiledata':user_profile}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user_profile = Profile.objects.get(user=request.user)
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=user_profile)

        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()
            messages.success(request, 'Profile Update Sucessfully!')
            return redirect('/accounts/profile/')  # Replace with your profile detail view name

        context = {'form': form,'userprofiledata':user_profile}
        return render(request, self.template_name, context)




    