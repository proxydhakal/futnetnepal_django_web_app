from multiprocessing import context
from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from apps.accounts.forms import UserRegisterForm
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


class UserProfileView(LoginRequiredMixin,ListView):
    model =Post
    template_name = 'account/profile.html'
    context_object_name = 'posts'
    ordering =['-created_at']

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).order_by('-created_at')
    