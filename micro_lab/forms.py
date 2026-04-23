from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']  # ✅ เพิ่ม 2 ตัวนี้

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ใส่ class + placeholder ให้ทุก field
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Enter username'
        })

        self.fields['email'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Enter email'
        })

        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Enter password'
        })

        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Confirm password'
        })