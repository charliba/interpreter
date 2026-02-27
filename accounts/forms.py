"""
accounts/forms.py — Formulários de autenticação (padrão waLink)
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


INPUT_CLASSES = (
    "w-full px-3 py-2.5 border border-gray-300 rounded-lg "
    "focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
)


class LoginForm(AuthenticationForm):
    """Formulário de login."""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Nome de usuário",
            "autocomplete": "username",
        }),
        error_messages={"required": "Username é obrigatório"},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Senha",
            "autocomplete": "current-password",
        }),
        error_messages={"required": "Senha é obrigatória"},
    )
    
    error_messages = {
        "invalid_login": "Usuário ou senha inválidos.",
        "inactive": "Conta desativada.",
    }


class RegisterForm(UserCreationForm):
    """Formulário de registro."""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Nome de usuário",
            "autocomplete": "username",
        }),
        error_messages={"required": "Username é obrigatório"},
    )
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Senha (mínimo 8 caracteres)",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Confirmar senha",
            "autocomplete": "new-password",
        }),
    )
    
    class Meta:
        model = User
        fields = ("username",)
