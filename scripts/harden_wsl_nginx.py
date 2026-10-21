"""Run inside WSL as root: add frontend headers and clear untrusted forwarded hosts."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import re
import ssl
import time
import urllib.request

path = Path('/etc/nginx/sites-enabled/mtls_demo.conf').resolve(strict=True)
if not path.is_relative_to('/etc/nginx') or not path.is_file():
    raise SystemExit('Unexpected nginx configuration target')
original = path.read_text()
headers = '''    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'none'; script-src 'self'; script-src-attr 'none'; style-src 'self'; style-src-attr 'none'; img-src 'self' https: http: data: blob:; font-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Strict-Transport-Security "max-age=86400" always;
'''
updated = original.replace('try_files $uri $uri/ /index.html;', 'try_files $uri /index.html;')
if '    index index.html;\n' not in updated:
    raise SystemExit('Expected index anchor missing; manual review needed')
updated = re.sub(r'^\s*add_header (?:X-Frame-Options|Content-Security-Policy|X-Content-Type-Options|Referrer-Policy|Strict-Transport-Security)\b[^\n]*\n', '', updated, flags=re.M)
updated = updated.replace('    index index.html;\n', '    index index.html;\n' + headers, 1)
if 'error_page 497' not in updated:
    updated = updated.replace('    listen 8443 ssl;', '    listen 8443 ssl;\n    server_tokens off;\n    error_page 497 =308 https://localhost:8443$request_uri;', 1)
if '# Local HTTP upgrade' not in updated:
    updated += '\n# Local HTTP upgrade\nserver {\n    listen 8088;\n    server_name localhost;\n    server_tokens off;\n    return 308 https://localhost:8443$request_uri;\n}\n'
updated = updated.replace('# Local HTTP upgrade\nserver {\n    listen 80;', '# Local HTTP upgrade\nserver {\n    listen 8088;')
if 'proxy_hide_header Content-Security-Policy;' not in updated:
    updated = updated.replace('    location /api/ {\n', '    location /api/ {\n' + ''.join(
        f'        proxy_hide_header {name};\n' for name in (
            'Content-Security-Policy', 'X-Frame-Options', 'X-Content-Type-Options',
            'Referrer-Policy', 'Strict-Transport-Security')), 1)

def verify_live_policy():
    ca = re.search(r'ssl_client_certificate\s+([^;]+);', updated).group(1)
    context = ssl.create_default_context(cafile=ca)
    for _ in range(20):
        try:
            with urllib.request.urlopen('https://localhost:8443/login', context=context, timeout=2) as response:
                if "default-src 'none'" in response.headers.get('Content-Security-Policy', ''):
                    return
        except OSError:
            pass
        time.sleep(0.25)
    raise RuntimeError('nginx reload did not activate the expected CSP; check its error log')
if 'proxy_set_header X-Forwarded-Host' not in updated:
    if '        proxy_set_header Host $host;\n' not in updated:
        raise SystemExit('Expected Host anchor missing; manual review needed')
    updated = updated.replace('        proxy_set_header Host $host;\n',
                              '        proxy_set_header Host $host;\n        proxy_set_header X-Forwarded-Host "";\n        proxy_set_header Forwarded "";\n', 1)
if updated != original:
    backup = path.with_name(path.name + '.week8-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.bak')
    shutil.copy2(path, backup)
    path.write_text(updated)
    try:
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['nginx', '-s', 'reload'], check=True)
        verify_live_policy()
    except Exception:
        path.write_text(original)
        subprocess.run(['nginx', '-s', 'reload'], check=False)
        raise
    print('Updated', path, '; backup:', backup)
else:
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['nginx', '-s', 'reload'], check=True)
    verify_live_policy()
    print('Headers and forwarding policy already configured.')
