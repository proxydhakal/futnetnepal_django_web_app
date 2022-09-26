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
            'location':Select(attrs={'class':'form-control custom-select mr-sm-2', 'id':'inlineFormCustomSelect'}),
            'venue':Select(attrs={'class':'form-control custom-select mr-sm-2', 'id':'inlineFormCustomSelect'}),
            'date':DateInput(attrs={'class':'form-control', 'id':'validationTooltip03', 'type':'date','placeholder':'Date'}),
            'time':Select(attrs={'class':'form-control custom-select mr-sm-2', 'id':'inlineFormCustomSelect'}),
            'message':Textarea(attrs={'class':'form-control','id':'exampleFormControlTextarea1', 'rows':'3'}),
        }

