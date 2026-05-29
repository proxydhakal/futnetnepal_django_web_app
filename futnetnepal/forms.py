from django import forms

from futnetnepal.input_validation import secure_clean_form_data


class SecureForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        return secure_clean_form_data(self, cleaned_data)


class SecureModelForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        return secure_clean_form_data(self, cleaned_data)
