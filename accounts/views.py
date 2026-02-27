"""
accounts/views.py — Views de autenticação (padrão waLink)
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegisterForm

logger = logging.getLogger(__name__)


def auth_page(request):
    """Página de login/registro — redireciona se já autenticado."""
    if request.user.is_authenticated:
        return redirect("upload")
    
    return render(request, "pages/auth.html", {
        "login_form": LoginForm(),
        "register_form": RegisterForm(),
        "active_tab": "login",
    })


@require_http_methods(["POST"])
def login_view(request):
    """POST — Autentica o usuário."""
    form = LoginForm(request, data=request.POST)
    
    if form.is_valid():
        user = form.get_user()
        request.session.flush()
        login(request, user)
        logger.info(f"Login: {user.username}")
        messages.success(request, f"Bem-vindo, {user.username}!")
        return redirect("upload")
    
    logger.warning(f"Login falhou: {request.POST.get('username', '?')}")
    
    return render(request, "pages/auth.html", {
        "login_form": form,
        "register_form": RegisterForm(),
        "active_tab": "login",
    })


@require_http_methods(["POST"])
def register_view(request):
    """POST — Cria novo usuário."""
    form = RegisterForm(request.POST)
    
    if form.is_valid():
        user = form.save()
        login(request, user)
        logger.info(f"Novo usuário: {user.username}")
        messages.success(request, f"Conta criada! Bem-vindo, {user.username}!")
        return redirect("upload")
    
    return render(request, "pages/auth.html", {
        "login_form": LoginForm(),
        "register_form": form,
        "active_tab": "register",
    })


@require_http_methods(["POST"])
def logout_view(request):
    """POST — Encerra sessão."""
    if request.user.is_authenticated:
        logger.info(f"Logout: {request.user.username}")
    logout(request)
    return redirect("auth_page")
