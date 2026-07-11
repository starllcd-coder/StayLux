from pathlib import Path
import sys, os

root = Path(__file__).resolve().parent
web_dir = root / "web"
if str(web_dir) not in sys.path:
    sys.path.insert(0, str(web_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "staylux.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = os.environ.get('DESK_USER', 'staylux')
password = os.environ.get('DESK_PASS', 'Kashmir@566')
email = os.environ.get('DESK_EMAIL', '')

if User.objects.filter(username=username).exists():
    print('exists')
else:
    User.objects.create_user(username, email, password)
    print('created')
