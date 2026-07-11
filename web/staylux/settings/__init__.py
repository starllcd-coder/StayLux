"""Settings package loader."""
from .loader import load_settings

"""Package shim for settings.

This package chooses the correct settings module (development or production)
and injects its UPPERCASE attributes into this package module so Django
can import `staylux.settings` as usual.
"""
from importlib import import_module
import os
from django.core.exceptions import ImproperlyConfigured


def _load():
	# Prefer the loader if present to keep logic centralized.
	try:
		loader = import_module("staylux.settings.loader")
		mod = loader.load_settings()
	except Exception:
		# Fallback: try importing staylux.settings (module) directly if present.
		env = os.environ.get("DJANGO_ENV", "development").lower()
		module_name = "staylux.settings.production" if env == "production" else "staylux.settings.development"
		mod = import_module(module_name)

	# Inject uppercase attributes
	for name in dir(mod):
		if name.isupper():
			globals()[name] = getattr(mod, name)

	# Basic production sanity check
	env = os.environ.get("DJANGO_ENV", "development").lower()
	if env == "production":
		if globals().get("DEBUG", False):
			raise ImproperlyConfigured("DEBUG must be False in production settings")


_load()

__all__ = ["load_settings"]