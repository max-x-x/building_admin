from django.conf import settings
import os

STATIC_URL = "/static/"
STATICFILES_DIRS = [settings.BASE_DIR / "core" / "static"]
STATIC_ROOT = os.path.join(settings.BASE_DIR, 'static')
