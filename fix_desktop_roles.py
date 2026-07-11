from pathlib import Path
import os
import sys

root = Path(__file__).resolve().parent
web_dir = root / "web"
if str(web_dir) not in sys.path:
    sys.path.insert(0, str(web_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "staylux.settings")
import django

django.setup()

from django.contrib.auth import get_user_model
from settings_app.models import PropertyProfile, BusinessType
from accounts.models import StaffProfile, StaffRole

username = os.environ.get("DESK_USER", "staylux")

User = get_user_model()
user = User.objects.filter(username=username).first()
if not user:
    raise SystemExit(f"User not found: {username}")

changed = False
if not user.is_superuser or not user.is_staff:
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])
    changed = True

prop = PropertyProfile.objects.first()
if not prop:
    prop = PropertyProfile.objects.create(
        name_en="StayLux Hotel",
        name_ar="",
        business_type=BusinessType.HOTEL,
        is_active=True,
    )
    changed = True

staff = StaffProfile.objects.filter(user=user).first()
if not staff:
    StaffProfile.objects.create(
        user=user,
        property=prop,
        role=StaffRole.OWNER_ADMIN,
        is_active=True,
    )
    changed = True
else:
    needs_save = False
    if staff.role != StaffRole.OWNER_ADMIN:
        staff.role = StaffRole.OWNER_ADMIN
        needs_save = True
    if staff.property_id != prop.id:
        staff.property = prop
        needs_save = True
    if not staff.is_active:
        staff.is_active = True
        needs_save = True
    if needs_save:
        staff.save(update_fields=["role", "property", "is_active"])
        changed = True

print("updated" if changed else "no_changes")
