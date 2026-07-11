import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'staylux.settings')
os.environ.setdefault('DJANGO_ENV', 'development')
import django
django.setup()
from django.conf import settings
import pprint

print('DJANGO_ENV =', os.environ.get('DJANGO_ENV'))
print('DEBUG =', getattr(settings, 'DEBUG', None))
print('INSTALLED_APPS:')
pprint.pprint(settings.INSTALLED_APPS)
