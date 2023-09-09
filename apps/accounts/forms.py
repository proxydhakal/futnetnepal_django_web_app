from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.forms import ModelForm, TextInput,PasswordInput
from apps.accounts.models import Profile

class EmailValidation(forms.EmailField):
    def validate(self, value):
        try:
            User.objects.get(email=value)
            raise forms.ValidationError("Email already Exist!")
        except User.DoesNotExist as e:
            pass

        except Exception as e:
            raise forms.ValidationError("Email already Exist!")

class UserRegisterForm(ModelForm):
    # email = EmailValidation(required=True)
    class Meta:
        model = User
        fields =['email','username','password']
        widgets ={
            'username':TextInput(attrs={'class':'form-control'}),
            'email':TextInput(attrs={'class':'form-control'}),
            'password':PasswordInput(attrs={'class':'form-control'}),
        }


    def clean_username(self):
        username = self.cleaned_data.get("username")
        qs = User.objects.filter(username__iexact=username)
        if qs.exists():
            raise forms.ValidationError(f"{username} is taken. Try another!")
        return username


    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = User.objects.filter(username__iexact=email)
        if qs.exists():
            raise forms.ValidationError(f"{email} is taken. Try another!")
        return email

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_image', 'cover_image', 'phone', 'address', 'dob']

class CombinedProfileUpdateForm(UserChangeForm):
    

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    profile = ProfileUpdateForm()

class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    profile_image = forms.ImageField(required=False)
    cover_image = forms.ImageField(required=False)
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(max_length=50, required=False)
    dob = forms.DateField(required=False)


