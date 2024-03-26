from django import forms
from django.contrib.auth.models import User
from apps.core.models import Post, Contact, Time, Location, Venue
from django.forms import ModelForm, TextInput,PasswordInput,DateInput,Select, Textarea


class UserPostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['location', 'venue', 'date', 'time', 'message']

    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=True)
    venue = forms.ModelChoiceField(queryset=Venue.objects.all(), required=True)
    date = forms.DateField(required=True)
    time = forms.ModelChoiceField(queryset=Time.objects.all(), required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        super(UserPostForm, self).__init__(*args, **kwargs)
        
        # Add Bootstrap classes to the widgets
        self.fields['location'].widget.attrs.update({'class': 'form-control'})
        self.fields['venue'].widget.attrs.update({'class': 'form-control'})
        self.fields['time'].widget.attrs.update({'class': 'form-control'})
        fields_to_check = ['location', 'venue', 'time']

        for field_name in fields_to_check:
            if self.errors.get(field_name):
                current_widget_classes = self.fields[field_name].widget.attrs.get('class', '')
                updated_widget_classes = current_widget_classes + ' is-invalid'
                self.fields[field_name].widget.attrs['class'] = updated_widget_classes



class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['fullname', 'email', 'phone','message']

    # Set required=True for the fields you want to be mandatory
    fullname = forms.CharField(max_length=255, required=True,)
    email = forms.EmailField(max_length=255, required=True)
    phone = forms.CharField(max_length=10, required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)


