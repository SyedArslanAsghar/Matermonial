"""App config replacing ``django.contrib.admin`` in INSTALLED_APPS: same "admin" label, with the
project's MFA- and role-aware default site (apps.admin_access.site). Kept free of model imports
because INSTALLED_APPS loads it before the app registry is ready."""

from django.contrib.admin.apps import AdminConfig


class MatermonialAdminConfig(AdminConfig):
    default_site = "apps.admin_access.site.MatermonialAdminSite"
