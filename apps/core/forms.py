from django import forms
from apps.core.models import Post, Contact, Time, Location, Venue, VenueBooking
from apps.accounts.forms import INPUT_CLASS

SELECT_CLASS = INPUT_CLASS
TEXTAREA_CLASS = INPUT_CLASS + ' min-h-[100px]'


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
        super().__init__(*args, **kwargs)
        select_attrs = {'class': SELECT_CLASS + ' fn-select2'}
        self.fields['location'].widget.attrs.update(select_attrs)
        self.fields['venue'].widget.attrs.update(select_attrs)
        self.fields['time'].widget.attrs.update(select_attrs)
        self.fields['date'].widget = forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'})
        self.fields['message'].widget.attrs.update({'class': TEXTAREA_CLASS, 'rows': 4, 'maxlength': 500})



class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['fullname', 'email', 'phone', 'message']

    fullname = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Full name'}))
    email = forms.EmailField(max_length=255, required=True, widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Email'}))
    phone = forms.CharField(max_length=10, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Phone'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'Your message', 'rows': 5}), required=True)


class VenueBookingForm(forms.ModelForm):
    class Meta:
        model = VenueBooking
        fields = ['booking_date', 'preferred_time', 'notes']
        widgets = {
            'booking_date': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'class': INPUT_CLASS, 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'rows': 3, 'placeholder': 'Optional notes'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['preferred_time'].required = True
        self.fields['notes'].required = False


