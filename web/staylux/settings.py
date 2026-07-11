"""Settings shim: choose development or production settings module.

This module loads either `staylux.settings.development` or
`staylux.settings.production` depending on the `DJANGO_ENV` env var.

Default: `development` (keeps SQLite and dev-friendly defaults).
Set `DJANGO_ENV=production` to enable strict production checks.
"""
from importlib import import_module
import os
from django.core.exceptions import ImproperlyConfigured

env = os.environ.get("DJANGO_ENV", "development").lower()
if env == "production":
    module_name = "staylux.settings.production"
else:
    module_name = "staylux.settings.development"

mod = import_module(module_name)

# Inject attributes from chosen module into this module's globals so Django
# can import settings as usual from `staylux.settings`.
globals().update({k: getattr(mod, k) for k in dir(mod) if k.isupper()})

if env == "production":
    # Basic runtime sanity checks
    if globals().get("DEBUG", False):
        raise ImproperlyConfigured("DEBUG must be False in production settings")
