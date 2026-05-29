from django import forms

from apps.accounts.forms import INPUT_CLASS
from apps.core.models import (
    Contact,
    Location,
    NewsletterSubscription,
    Post,
    Time,
    UserReview,
    Venue,
    VenueBooking,
)
from futnetnepal.forms import SecureModelForm

SELECT_CLASS = INPUT_CLASS
TEXTAREA_CLASS = INPUT_CLASS + ' min-h-[100px]'


class UserPostForm(SecureModelForm):
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



class ContactForm(SecureModelForm):
    class Meta:
        model = Contact
        fields = ['fullname', 'email', 'phone', 'subject', 'message']

    fullname = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Full name'}))
    email = forms.EmailField(max_length=255, required=True, widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Email'}))
    phone = forms.CharField(max_length=10, required=True, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Phone'}))
    subject = forms.ChoiceField(
        choices=Contact.SUBJECT_CHOICES,
        required=True,
        label='Subject',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    message = forms.CharField(widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'Your message', 'rows': 5}), required=True)


class NewsletterSubscriptionForm(SecureModelForm):
    class Meta:
        model = NewsletterSubscription
        fields = ['name', 'email']

    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Your name', 'autocomplete': 'name'}),
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'autocomplete': 'email'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if NewsletterSubscription.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already subscribed to our newsletter.')
        return email


class UserReviewForm(SecureModelForm):
    RATING_CHOICES = [(i, f'{i} star{"s" if i != 1 else ""}') for i in range(1, 6)]

    class Meta:
        model = UserReview
        fields = ['name', 'email', 'rating', 'message']

    name = forms.CharField(
        max_length=255,
        required=True,
        label='Your name',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Full name', 'autocomplete': 'name'}),
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Email', 'autocomplete': 'email'}),
    )
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        required=True,
        label='Rating',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    message = forms.CharField(
        label='Your review',
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASS, 'placeholder': 'Share your experience with Futnet Nepal', 'rows': 5}),
        required=True,
    )

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if rating < UserReview.RATING_MIN or rating > UserReview.RATING_MAX:
            raise forms.ValidationError('Please choose a rating between 1 and 5 stars.')
        return rating

    def clean_email(self):
        return self.cleaned_data['email'].lower().strip()


class VenueBookingForm(SecureModelForm):
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


