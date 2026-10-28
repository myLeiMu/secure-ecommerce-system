"""Read-only probes of actual local TLS gateways; no credentials in evidence."""
import json
import os
from pathlib import Path
import re

import requests

root = Path(__file__).resolve().parents[1]
session = requests.Session()
session.trust_env = False
session.verify = str(root / 'keys/mtls_local/classroom-ca.crt')
checks = []
dev_port = int(os.environ.get('FRONTEND_DEV_PORT', '3000'))
dev_base = f'https://localhost:{dev_port}'


def check(name, passed, **details):
    checks.append({'name': name, 'passed': bool(passed), **details})


for port in (dev_port, 8443):
    base = f'https://localhost:{port}'
    for path in ('/', '/login', '/products'):
        response = session.get(base + path, timeout=15)
        csp = response.headers.get('Content-Security-Policy', '')
        required = ("default-src 'none'", "script-src 'self'", "style-src 'self'",
                    "form-action 'self'", "frame-ancestors 'none'", "object-src 'none'")
        check(f'{port} {path} TLS + CSP', response.status_code == 200 and all(value in csp for value in required)
              and 'unsafe-inline' not in csp and 'unsafe-eval' not in csp,
              status=response.status_code, csp=csp, hsts=response.headers.get('Strict-Transport-Security'))
    response = session.get(base + '/api/health/', timeout=15)
    check(f'{port} API health through same-origin proxy', response.status_code == 200
          and 'application/json' in response.headers.get('Content-Type', ''), status=response.status_code)
    response = session.get(base + '/api/admin/users', timeout=15)
    check(f'{port} anonymous admin API denied', response.status_code == 401, status=response.status_code)
first = session.get(dev_base + '/login', timeout=15)
second = session.get(dev_base + '/login', timeout=15)
nonce = re.search(r"'nonce-([^']+)'", first.headers['Content-Security-Policy']).group(1)
check('development nonce matches HTML and changes each response', nonce in first.text
      and nonce not in second.headers['Content-Security-Policy'] and '__RESPONSE_CSP_NONCE__' not in first.text)
response = session.get(dev_base + '/', headers={'Host': 'attacker.invalid'}, timeout=15)
check('development rejects unknown Host', response.status_code == 403, status=response.status_code)
try:
    response = session.get(f'http://localhost:{dev_port}/login', timeout=5, allow_redirects=False)
    check(f'HTTP {dev_port} does not serve login', response.status_code >= 400, status=response.status_code)
except requests.ConnectionError:
    check(f'HTTP {dev_port} does not serve login', True, connection='TLS-only listener closed plaintext connection')
for headers in ({}, {'X-Forwarded-Proto': 'https'}, {'X-Forwarded-Proto': 'https', 'X-MTLS-PROXY-SECRET': 'forged'}):
    response = session.post('http://127.0.0.1:8080/api/auth/login', json={}, headers=headers, timeout=15)
    check('plaintext/spoofed gateway POST rejected', response.status_code == 426, status=response.status_code)
response = session.get('http://localhost:8088/login', allow_redirects=False, timeout=10)
check('HTTP 8088 upgrades to fixed HTTPS host', response.status_code == 308
      and response.headers.get('Location') == 'https://localhost:8443/login', status=response.status_code)
report = root / os.environ.get('EVIDENCE_DIR', 'docs/evidence/local-https-check') / 'https-gateways.json'
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'passed': sum(item['passed'] for item in checks), 'total': len(checks),
                  'failed': [item['name'] for item in checks if not item['passed']]}))
raise SystemExit(0 if all(item['passed'] for item in checks) else 1)
