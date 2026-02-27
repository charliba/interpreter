"""accounts/urls.py — Rotas de autenticação"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.auth_page, name="auth_page"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
]
