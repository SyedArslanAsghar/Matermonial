import os

from django.core.wsgi import get_wsgi_application

# Deployment entry point: defaults to production settings, which fail closed (KI-8).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_wsgi_application()
