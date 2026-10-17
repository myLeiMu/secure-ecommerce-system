"""Run inside WSL as root: add frontend headers and clear untrusted forwarded hosts."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

path = Path('/etc/nginx/sites-enabled/mtls_demo.conf').resolve(strict=True)
if not path.is_relative_to('/etc/nginx') or not path.is_file():
    raise SystemExit('Unexpected nginx configuration target')
original = path.read_text()
headers = '''    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "frame-ancestors 'none'; object-src 'none'; base-uri 'self'" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
'''
updated = original.replace('try_files $uri $uri/ /index.html;', 'try_files $uri /index.html;')
if 'add_header Content-Security-Policy' not in updated:
    if '    index index.html;\n' not in updated:
        raise SystemExit('Expected index anchor missing; manual review needed')
    updated = updated.replace('    index index.html;\n', '    index index.html;\n' + headers, 1)
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
    except Exception:
        path.write_text(original)
        raise
    print('Updated', path, '; backup:', backup)
else:
    subprocess.run(['nginx', '-t'], check=True)
    print('Headers and forwarding policy already configured.')
