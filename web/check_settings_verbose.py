import os
import sys
import pprint

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'staylux.settings')
os.environ.setdefault('DJANGO_ENV', 'development')

print('ENV VARS:')
for k in ('DJANGO_ENV', 'DJANGO_DEBUG', 'DB_ENGINE', 'DB_NAME'):
    print(f'{k} =', repr(os.environ.get(k)))

import importlib
try:
    mod = importlib.import_module('staylux.settings')
except Exception as e:
    print('Error importing staylux.settings:', e)
    raise

print('\nImported module:', mod.__name__)
print('Module file:', getattr(mod, '__file__', None))

print('\nModule ATTRS:')
attrs = {k: getattr(mod, k) for k in dir(mod) if k.isupper()}
pprint.pprint({k: (v if k not in ('INSTALLED_APPS',) else list(v)) for k, v in attrs.items()})

import django
try:
    django.setup()
except Exception as e:
    print('\ndjango.setup() raised:', repr(e))

from django.conf import settings

print('\nDjango settings object:')
print('settings module (wrapped):', settings._wrapped.__class__ if hasattr(settings, '_wrapped') else type(settings))
print('DEBUG =', getattr(settings, 'DEBUG', None))
print('INSTALLED_APPS =')
pprint.pprint(getattr(settings, 'INSTALLED_APPS', None))

print('\nLoaded sys.modules entries for staylux.settings*:')
for name in sorted(k for k in sys.modules if k.startswith('staylux.settings')):
    m = sys.modules[name]
    print(name, '->', getattr(m, '__file__', None))
