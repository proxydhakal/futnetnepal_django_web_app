from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from apps.core.models import Post
from django.forms import ModelForm, TextInput,PasswordInput,DateInput,Select, Textarea


class UserPostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['location', 'venue', 'date', 'time', 'message']
        widgets = {
            'location': forms.Select(attrs={'class': 'form-control custom-select mr-sm-2', 'id': 'inlineFormCustomSelect'}),
            'venue': forms.Select(attrs={'class': 'form-control custom-select mr-sm-2', 'id': 'inlineFormCustomSelect'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'id': 'validationTooltip03', 'type': 'date', 'placeholder': 'Date'}),
            'time': forms.Select(attrs={'class': 'form-control custom-select mr-sm-2', 'id': 'inlineFormCustomSelect'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'id': 'exampleFormControlTextarea1', 'rows': '3'}),
        }

    # Add required attribute to all fields
    location = forms.CharField(widget=forms.Select(attrs={'class': 'form-control custom-select mr-sm-2', 'id': 'inlineFormCustomSelect', 'required': 'required'}))
    venue = forms.CharField(widget=forms.Select(attrs={'class': 'form-control custom-select mr-sm-2', 'id': 'inlineFormCustomSelect', 'required': 'required'}))
    date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'id': 'validationTooltip03', 'type': 'date', 'placeholder': 'Date', 'required': 'required'}))
    time = forms.CharField(widget=forms.Select(attrs={'class': 'form-control custom-select mr-sm-2', 'id': 'inlineFormCustomSelect', 'required': 'required'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'id': 'exampleFormControlTextarea1', 'rows': '3', 'required': 'required'}))

