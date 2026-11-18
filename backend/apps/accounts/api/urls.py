"""/api/v1/auth/ routes (doc 04 §2)."""

from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("otp/send/", views.OtpSendView.as_view(), name="auth-otp-send"),
    path("otp/verify/", views.OtpVerifyView.as_view(), name="auth-otp-verify"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
]
