from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class SignUpForm(forms.Form):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('The passwords do not match.')
        return cleaned_data


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            user = User.objects.filter(email__iexact=email.strip()).first()
            if user and user.check_password(password):
                self.user_cache = user
            else:
                raise forms.ValidationError('Invalid email or password.')
        return self.cleaned_data


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        label='Verification Code',
        widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'placeholder': '123456'}),
    )
