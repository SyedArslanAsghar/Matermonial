import os

from django.core.asgi import get_asgi_application

# Deployment entry point: defaults to production settings, which fail closed (KI-8).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_asgi_application()
