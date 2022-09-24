from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from apps.core.models import Post
from django.forms import ModelForm, TextInput,PasswordInput,DateInput,Select, Textarea


class UserPostForm(ModelForm):
    class Meta:
        model = Post
        fields =['location','venue','date','time','message']
        widgets ={
            'location':Select(attrs={'class':'form-control'}),
            'venue':Select(attrs={'class':'form-control'}),
            'date':DateInput(attrs={'class':'form-control'}),
            'time':Select(attrs={'class':'form-control'}),
            'message':Textarea(attrs={'class':'form-control'}),
        }

