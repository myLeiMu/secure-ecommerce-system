"""Record effective Django security settings without dumping any secrets."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'api_service'))
from service import settings

parser = argparse.ArgumentParser()
parser.add_argument('--label', choices=('baseline', 'regression'), required=True)
args = parser.parse_args()
report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'effective_debug': settings.DEBUG,
          'django_secret_key_configured': bool(os.getenv('DJANGO_SECRET_KEY')),
          'django_secret_key_strong': (len(settings.SECRET_KEY) >= 50 and
                                       len(set(settings.SECRET_KEY)) >= 5 and
                                       not settings.SECRET_KEY.startswith('django-insecure-')),
          'session_cookie_secure': settings.SESSION_COOKIE_SECURE,
          'csrf_cookie_secure': settings.CSRF_COOKIE_SECURE,
          'allowed_hosts': settings.ALLOWED_HOSTS,
          'note': 'Boolean configuration check; secret values are never included.'}
destination = ROOT / f'docs/evidence/week7/config-{args.label}.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(destination, 'DEBUG=', report['effective_debug'])
