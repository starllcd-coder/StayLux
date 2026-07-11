import os
from importlib import import_module


def load_settings():
    env = os.environ.get("DJANGO_ENV", "development").lower()
    if env == "production":
        module = "staylux.settings.production"
    else:
        module = "staylux.settings.development"
    mod = import_module(module)
    return mod


# When Django imports staylux.settings, it expects module-level attributes.
# This loader exposes them by importing the chosen module and injecting
# its attributes into the current globals when called from the shim.