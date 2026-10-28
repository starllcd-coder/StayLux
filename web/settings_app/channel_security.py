from django.conf import settings
from cryptography.fernet import Fernet


def credential_cipher():
    key = settings.CHANNEL_CREDENTIALS_KEY
    if not key:
        raise ValueError("Channel credential storage is not configured")
    return Fernet(key.encode())


def credential_storage_ready():
    try:
        credential_cipher()
        return True
    except (ValueError, TypeError):
        return False


def check_channel_setup(config):
    """Local checks only; never claims to verify a remote connection."""
    issues = []
    if not config.external_property_id:
        issues.append("Enter the external property / hotel ID.")
    if not config.unit_mappings:
        issues.append("Map at least one room or listing.")
    else:
        from inventory.models import Unit
        actual_units = set(str(pk) for pk in Unit.objects.filter(property_profile=config.property_profile).values_list("pk", flat=True))
        if any(pk not in actual_units or not mapping.get("room_id") for pk, mapping in config.unit_mappings.items()):
            issues.append("Each mapping must reference a room in this property and include its external room/listing ID.")
    try:
        credentials = config.get_credentials()
    except Exception:
        credentials = {}
        issues.append("Stored credentials cannot be opened. Check the server encryption key.")
    required = {"api_token": ["access_token"], "oauth": ["client_id", "client_secret"], "machine_account": ["api_username", "api_password"]}
    if any(not credentials.get(key) for key in required[config.authentication_method]):
        issues.append("Supply the API credentials required by the selected authentication method.")
    return issues
