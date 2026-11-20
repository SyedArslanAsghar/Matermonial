"""/api/v1/auth/ routes (doc 04 §2)."""

from django.urls import path

from . import mfa, views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("otp/send/", views.OtpSendView.as_view(), name="auth-otp-send"),
    path("otp/verify/", views.OtpVerifyView.as_view(), name="auth-otp-verify"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("token/refresh/", views.RefreshView.as_view(), name="auth-token-refresh"),
    path("sessions/", views.SessionListView.as_view(), name="auth-sessions"),
    path("sessions/revoke-others/", views.RevokeOthersView.as_view(), name="auth-revoke-others"),
    path("sessions/<uuid:session_id>/", views.SessionDetailView.as_view(), name="auth-session"),
    path("reauthenticate/", views.ReauthenticateView.as_view(), name="auth-reauthenticate"),
    path("password/forgot/", views.PasswordForgotView.as_view(), name="auth-password-forgot"),
    path("password/reset/", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path("password/change/", views.PasswordChangeView.as_view(), name="auth-password-change"),
    path("mfa/", mfa.MfaStatusView.as_view(), name="auth-mfa"),
    path("mfa/enroll/", mfa.MfaEnrollView.as_view(), name="auth-mfa-enroll"),
    path("mfa/confirm/", mfa.MfaConfirmView.as_view(), name="auth-mfa-confirm"),
    path("mfa/remove/", mfa.MfaRemoveView.as_view(), name="auth-mfa-remove"),
]
