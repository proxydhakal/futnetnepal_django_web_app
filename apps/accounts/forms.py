from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from apps.accounts.models import Profile, User
from futnetnepal.forms import SecureForm, SecureModelForm
from apps.accounts.phone_verification import PhoneVerificationError, normalize_phone

UserModel = get_user_model()

INPUT_CLASS = 'fn-input w-full mt-1 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-500 focus:bg-white'


class LoginForm(SecureForm):
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
            if profile is not None and not self.user_cache.is_email_verified:
                raise forms.ValidationError(
                    'Please verify your email before logging in. '
                    'Check your inbox or request a new verification link.',
                    code='email_unverified',
                )
            if profile is not None and profile.phone and not profile.phone_verified:
                raise forms.ValidationError(
                    'Please verify your phone number before logging in.',
                    code='phone_unverified',
                )
        return cleaned

    def get_user(self):
        return self.user_cache


class RegisterForm(SecureForm, UserCreationForm):
    full_name = forms.CharField(
        max_length=300,
        required=True,
        label='Full name',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Your full name',
            'autocomplete': 'name',
            'required': True,
        }),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Email address',
            'autocomplete': 'email',
            'required': True,
        }),
    )
    phone = forms.CharField(
        max_length=10,
        required=True,
        label='Mobile number',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': '9840123456',
            'inputmode': 'numeric',
            'maxlength': '10',
            'autocomplete': 'tel',
            'required': True,
        }),
    )

    class Meta(UserCreationForm.Meta):
        model = UserModel
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
        self.fields['username'].help_text = ''
        self.fields['password1'].required = True
        self.fields['password2'].required = True
        self.fields['password1'].help_text = ''
        self.fields['password1'].widget.attrs.update({
            'id': 'id_password1',
            'data-password-hint': 'true',
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
        if UserModel.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email.lower()

    def clean_phone(self):
        try:
            return normalize_phone(self.cleaned_data['phone'])
        except PhoneVerificationError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.role = User.Role.USER
        if commit:
            user.save()
            profile = Profile.objects.get(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.phone_verified = False
            profile.save(update_fields=['phone', 'phone_verified'])
        return user


class UserProfileUpdateForm(SecureModelForm):
    profile_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-slate-600'}),
    )

    class Meta:
        model = Profile
        fields = ['cover_image', 'phone', 'address', 'dob']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'inputmode': 'numeric',
                'placeholder': '9840123456',
                'maxlength': '10',
            }),
            'address': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'dob': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'cover_image': forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-slate-600'}),
        }

    def clean_phone(self):
        raw = (self.cleaned_data.get('phone') or '').strip()
        if not raw:
            return ''
        try:
            return normalize_phone(raw)
        except PhoneVerificationError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def save(self, commit=True):
        instance = self.instance
        old_phone = instance.phone if instance.pk else ''
        profile = super().save(commit=False)
        if self.files.get('profile_image'):
            profile.user.profile_image = self.files['profile_image']
            profile.user.save(update_fields=['profile_image'])
        if commit:
            profile.save()
            if profile.phone != old_phone:
                profile.phone_verified = False
                profile.phone_otp_hash = ''
                profile.phone_otp_sent_at = None
                profile.phone_otp_attempts = 0
                profile.save(update_fields=[
                    'phone_verified', 'phone_otp_hash', 'phone_otp_sent_at', 'phone_otp_attempts',
                ])
        return profile


class UserUpdateForm(SecureModelForm):
    class Meta:
        model = UserModel
        fields = ['username', 'email', 'full_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'full_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Your full name',
            }),
        }


class StyledPasswordChangeForm(SecureForm, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = INPUT_CLASS


class StyledPasswordResetForm(SecureForm, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['email'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
            'required': True,
        })


class StyledSetPasswordForm(SecureForm, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
            field.widget.attrs.update({
                'class': INPUT_CLASS,
                'required': True,
                'autocomplete': 'new-password',
            })
