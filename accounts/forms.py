from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import *

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter password",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email"]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Username",
                    "autocomplete": "username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Email address",
                    "autocomplete": "email",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password, User())
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your registered email",
                "autocomplete": "email",
                "required": True,
            }
        ),
    )
