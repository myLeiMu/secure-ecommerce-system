"""Read-only HTTPS header evidence; never saves response bodies or credentials."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', choices=['before', 'after'], required=True)
args = parser.parse_args()
session = requests.Session()
session.trust_env = False
checks = []
for path in ['/', '/products', '/products/', '/login', '/api/health/']:
    try:
        response = session.get('https://localhost:8443' + path, timeout=10,
                               verify=str(ROOT / 'keys/mtls_local/classroom-ca.crt'), allow_redirects=False)
        checks.append({'path': path, 'status': response.status_code,
                       'headers': {key: response.headers.get(key) for key in
                                   ['Content-Type', 'X-Frame-Options', 'Content-Security-Policy', 'X-Content-Type-Options']}})
    except requests.RequestException as exc:
        checks.append({'path': path, 'error_type': type(exc).__name__})
passed = all(c.get('status') in (200, 301, 302) and c.get('headers', {}).get('X-Frame-Options') == 'DENY'
             and "frame-ancestors 'none'" in (c.get('headers', {}).get('Content-Security-Policy') or '') for c in checks[:4])
report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'tls_verification_required': True,
          'entry': 'https://localhost:8443', 'checks': checks, 'frontend_headers_passed': passed,
          'scope': 'Targeted header verification, not a full Burp rescan; API health status reported separately.'}
out = ROOT / f'docs/evidence/week8/gateway-{args.label}.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(out, 'frontend_headers_passed=', passed)
