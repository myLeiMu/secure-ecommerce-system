"""Developer smoke check against real WSL nginx; outputs no credentials or MFA secrets."""
import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path

root = Path(__file__).resolve().parents[1]
certs = root / 'keys' / 'mtls_local'
results = []

def call(name, account=None, body=None, path='/api/auth/cert/mtls-login', token=None, expected=200, method='POST', extra=None):
    context = ssl.create_default_context(cafile=str(certs / 'classroom-ca.crt'))
    if account:
        context.load_cert_chain(str(certs / f'{account}.crt'), str(certs / f'{account}.key'))
    headers = {'Content-Type': 'application/json', **(extra or {})}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request('https://localhost:8443'+path, data=json.dumps(body or {}).encode() if method == 'POST' else None,
                                     headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=context, timeout=30) as response:
            status, payload = response.status, json.load(response)
    except urllib.error.HTTPError as response:
        status, payload = response.code, json.load(response)
    row = {'case': name, 'status': status, 'expected': expected}
    data = payload.get('data') or {}
    if path.endswith('mtls-login'):
        row.update(token_returned=bool(data.get('token')), mfa_required=bool(data.get('mfa_required')))
    results.append(row)
    assert status == expected, (name, status, payload.get('message'))
    return data

call('No certificate cannot fake nginx verification', expected=401, extra={'X-SSL-CLIENT-VERIFY': 'SUCCESS', 'X-SSL-CLIENT-S-DN': 'CN=week1_admin'})
buyer = call('Buyer certificate login', 'week1_buyer', {'username': 'week1_buyer'})
assert buyer['token'] and buyer['user']['role'] == 'normal'
call('Buyer cannot impersonate admin', 'week1_buyer', {'username': 'week1_admin'}, expected=401)
call('Buyer forbidden platform admin', 'week1_buyer', path='/api/admin/users', token=buyer['token'], expected=403, method='GET')
call('Buyer own listings', 'week1_buyer', path='/api/merchant/products', token=buyer['token'], method='GET')
for account in ('week1_admin', 'week1_auditor'):
    pending = call(account+' waits for TOTP', account, {'username': account})
    assert pending['mfa_required'] and 'token' not in pending
output = root / 'docs' / 'evidence' / 'live-mtls.json'
output.write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results, indent=2))
