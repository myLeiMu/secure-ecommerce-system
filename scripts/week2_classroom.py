"""Isolated classroom evidence: real SM2 signatures, Django API, disposable SQLite.

python scripts/week2_classroom.py [--serve]
No real users, CA, MFA bindings or business data are modified.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_service.tests.test_course_security import CourseSecurityTests
from api_service.api.security_core import totp
from src.Data_base.database import SessionLocal
from src.Data_base.models.user import User
from src.Data_base.models.security import AuditEvent
from src.algorithm.ca_center import create_root_ca, create_csr, issue_certificate_from_csr
from gmssl import sm2, func


def run(serve=False):
    fixture = CourseSecurityTests()
    records = []
    output = ROOT / 'docs' / 'evidence' / 'week2'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='week2-cert-') as temporary:
        fixture.setUp()
        try:
            with SessionLocal.begin() as db:
                for uid in (2, 5):
                    db.get(User, uid).user_role = 'normal'
            root_key, root_cert = create_root_ca(common_name='Classroom CA', organization='Classroom', country='CN')
            root_path = Path(temporary) / 'root.pem'
            root_path.write_text(root_cert.to_pem(), encoding='utf-8')
            materials = {}
            for username in ('user1', 'user4'):
                private = func.random_hex(64)
                signer = sm2.CryptSM2(public_key='', private_key=private)
                public = signer._kg(int(private, 16), signer.ecc_table['g'])
                csr = create_csr(username, 'Classroom', 'CN', private, public)
                cert = issue_certificate_from_csr(csr=csr, issuer_common_name='Classroom CA',
                    issuer_organization='Classroom', issuer_country='CN', issuer_private_key_hex=root_key,
                    issuer_public_key_hex=root_cert.subject_public_key_hex, is_ca=False, years_valid=1)
                materials[username] = (signer, cert.to_pem())

            def request(label, path, body=None, token=None, method='POST', expected=200):
                status, response = fixture.request(path, body, token=token, method=method)
                records.append({'case': label, 'method': method, 'path': path,
                                'expected': expected, 'actual': status, 'passed': status == expected})
                if status != expected:
                    raise AssertionError(f'{label}: expected {expected}, actual {status}: {response.get("message")}')
                return response.get('data')

            def certificate_login(username, bad_signature=False):
                data = request('certificate challenge', '/api/auth/cert/challenge', {'username': username})
                signer, cert = materials[username]
                signature = signer.sign(data['challenge'].encode(), func.random_hex(64))
                if bad_signature:
                    signature = '0' * len(signature)
                return request('SM2 signature rejected' if bad_signature else f'{username} certificate login',
                    '/api/auth/cert/login', {'username': username, 'certificate_pem': cert,
                    'challenge': data['challenge'], 'signature_hex': signature}, expected=401 if bad_signature else 200)

            with patch.dict(os.environ, {'CA_ROOT_CERT_PATH': str(root_path)}):
                certificate_login('user4', bad_signature=True)
                trader = certificate_login('user1')['token']
                request('trader denied platform management', '/api/admin/users', token=trader, method='GET', expected=403)
                request('trader denied audit', '/api/audit/events', token=trader, method='GET', expected=403)
                request('trader own order allowed', '/api/orders/1', token=trader, method='GET')
                request('trader own listings allowed', '/api/merchant/products', token=trader, method='GET')
                request('trader cannot edit another seller listing', '/api/merchant/products/1',
                        {'product_name': 'forbidden'}, token=trader, method='PUT', expected=403)
                pending = certificate_login('user4')
                assert pending['mfa_required'] and 'token' not in pending
                records.append({'case': 'certificate alone issues no privileged JWT', 'passed': True})
                request('MFA alone without challenge denied', '/api/auth/mfa/verify', {'code': '123456'}, expected=400)
                request('incorrect MFA denied', '/api/auth/mfa/verify',
                        {'challenge': pending['challenge'], 'code': 'invalid'}, expected=400)
                code = totp(pending['secret'], int(time.time()) // 30)
                body = {'challenge': pending['challenge'], 'code': code}
                verified = request('correct MFA allows login', '/api/auth/mfa/verify', body)
                assert verified['user']['mfa']
                request('consumed challenge replay denied', '/api/auth/mfa/verify', body, expected=400)
                audit_token = verified['token']
                request('auditor audit allowed', '/api/audit/events', token=audit_token, method='GET')
                request('auditor platform management denied', '/api/admin/users', token=audit_token, method='GET', expected=403)
                request('auditor order creation denied', '/api/orders', {}, token=audit_token, expected=403)
                request('auditor listing management denied', '/api/merchant/products', token=audit_token, method='GET', expected=403)
                pending = certificate_login('user4')
                request('old TOTP in new challenge denied', '/api/auth/mfa/verify',
                        {'challenge': pending['challenge'], 'code': code}, expected=400)
                recovery = verified['recovery_codes'][0]
                request('one-time recovery allows login', '/api/auth/mfa/verify',
                        {'challenge': pending['challenge'], 'code': recovery})
                pending = certificate_login('user4')
                request('used recovery rejected', '/api/auth/mfa/verify',
                        {'challenge': pending['challenge'], 'code': recovery}, expected=400)
                with SessionLocal() as db:
                    events = [{'action': e.action, 'username': e.username, 'result': e.result,
                               'resource': e.resource, 'time': e.created_at.isoformat()}
                              for e in db.query(AuditEvent).order_by(AuditEvent.event_id)]
                for event in ('MFA_SUCCESS', 'MFA_FAILED', 'MFA_REPLAY'):
                    assert any(e['action'] == event for e in events), event
                records.append({'case': 'required MFA audit events recorded', 'passed': True})
                output.joinpath('results.json').write_text(json.dumps({'environment': 'isolated SQLite and temporary SM2 CA; real certificate and signature verification',
                    'cases': records, 'audit': events}, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'PASS: {len(records)} checks; report: {output / "results.json"}')
                if serve:
                    # Admin user3 is intentionally not enrolled; open the real UI to view audit evidence.
                    import mimetypes
                    from urllib.parse import unquote
                    from wsgiref.simple_server import make_server
                    from django.core.wsgi import get_wsgi_application
                    application = get_wsgi_application()
                    dist = (ROOT / 'frontend' / 'dist').resolve()
                    def app(environ, start_response):
                        if environ.get('PATH_INFO', '').startswith('/api/'):
                            return application(environ, start_response)
                        target = (dist / unquote(environ.get('PATH_INFO', '/')).lstrip('/')).resolve()
                        if not target.is_relative_to(dist):
                            start_response('403 Forbidden', [])
                            return [b'Forbidden']
                        if not target.is_file():
                            target = dist / 'index.html'
                        start_response('200 OK', [('Content-Type', mimetypes.guess_type(str(target))[0] or 'application/octet-stream')])
                        return [target.read_bytes()]
                    print('Preview http://127.0.0.1:8766/login; admin user3 / TestPass123! (fresh MFA enrollment)', flush=True)
                    with make_server('127.0.0.1', 8766, app) as server:
                        server.serve_forever()
        finally:
            fixture.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Keep isolated data available for browser screenshots on port 8766')
    args = parser.parse_args()
    run(args.serve)
