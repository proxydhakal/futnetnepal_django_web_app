from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User

from apps.accounts.models import Profile

INPUT_CLASS = 'fn-input w-full mt-1 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-500 focus:bg-white'


class LoginForm(forms.Form):
    login = forms.CharField(
        label='Username or email',
        max_length=254,
        required=True,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Username or email',
            'autocomplete': 'username',
            'required': True,
        }),
    )
    password = forms.CharField(
        label='Password',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Password',
            'autocomplete': 'current-password',
            'required': True,
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        login = cleaned.get('login')
        password = cleaned.get('password')
        if login and password:
            self.user_cache = authenticate(
                self.request,
                login=login.strip(),
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Invalid username/email or password. Please try again.',
                )
            profile = getattr(self.user_cache, 'profile', None)
            if profile is not None and not profile.email_verified:
                raise forms.ValidationError(
                    'Please verify your email before logging in. '
                    'Check your inbox or request a new verification link.',
                    code='email_unverified',
                )
        return cleaned

    def get_user(self):
        return self.user_cache


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Email address',
            'autocomplete': 'email',
            'required': True,
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Username',
                'autocomplete': 'username',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = True
        self.fields['password1'].required = True
        self.fields['password2'].required = True
        self.fields['password1'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'Password',
            'autocomplete': 'new-password',
            'required': True,
        })
        self.fields['password2'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password',
            'required': True,
        })

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email.lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_image', 'cover_image', 'phone', 'address', 'dob']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'inputmode': 'numeric',
                'placeholder': '9840123456',
                'maxlength': '10',
            }),
            'address': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'dob': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'profile_image': forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-slate-600'}),
            'cover_image': forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-slate-600'}),
        }

    def clean_phone(self):
        raw = (self.cleaned_data.get('phone') or '').strip()
        if not raw:
            return ''
        digits = ''.join(c for c in raw if c.isdigit())
        if not digits:
            return ''
        if len(digits) > 10:
            raise forms.ValidationError('Phone number must be at most 10 digits.')
        return digits


def _split_full_name(full_name):
    full_name = (full_name or '').strip()
    if not full_name:
        return '', ''
    parts = full_name.split(None, 1)
    return parts[0], parts[1] if len(parts) > 1 else ''


class UserUpdateForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=300,
        required=True,
        label='Full name',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your full name'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['full_name'].initial = self.instance.get_full_name() or ''

    def save(self, commit=True):
        user = super().save(commit=False)
        first, last = _split_full_name(self.cleaned_data.get('full_name', ''))
        user.first_name = first
        user.last_name = last
        if commit:
            user.save()
        return user


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = INPUT_CLASS


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['email'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
            'required': True,
        })


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({
                'class': INPUT_CLASS,
                'required': True,
                'autocomplete': 'new-password',
            })
