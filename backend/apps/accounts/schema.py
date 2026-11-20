"""OpenAPI security schemes for the custom authentication classes (KI-40).

drf-spectacular discovers ``OpenApiAuthenticationExtension`` subclasses on import; this module
is imported by ``AccountsConfig.ready``. The schemes describe what the classes actually accept:
the web session cookie (with CSRF for unsafe methods) and the mobile Bearer access token."""

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class WebSessionScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.WebSessionAuthentication"
    name = "webSession"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.SESSION_COOKIE_NAME,
            "description": "Web session cookie; unsafe methods also need the CSRF header.",
        }


class BearerTokenScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.BearerTokenAuthentication"
    name = "bearerToken"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "description": "Mobile access token from /api/v1/auth/login/ (client_type MOBILE).",
        }
