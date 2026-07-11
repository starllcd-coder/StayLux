import os
import json
import sys
from pathlib import Path

# Ensure Django project package is importable
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / 'web'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'staylux.settings')
import django
django.setup()

from django.test import Client

def run():
    c = Client()
    r = c.post('/api/mobile/auth/login/', json.dumps({'email':'admin@staylux.com','password':'Kashmir@566'}), content_type='application/json')
    print('STATUS', r.status_code)
    try:
        print('JSON', r.json())
    except Exception as e:
        print('JSON_ERROR', e)
    print('LENGTH', len(r.content))
    print(r.content.decode(errors='replace'))

if __name__ == '__main__':
    run()
