"""Bounded HTTP probes against an ephemeral SQLite fixture, never real accounts."""
import argparse
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from wsgiref.simple_server import make_server

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_service.tests.test_course_security import CourseSecurityTests, SessionLocal, User
from django.core.wsgi import get_wsgi_application


def scan(base, token_a, token_b, label):
    checks = []

    def probe(name, method, path, token=None, **kwargs):
        headers = dict(kwargs.pop('headers', {}))
        if token:
            headers['Authorization'] = 'Bearer ' + token
        response = requests.request(method, base + path, headers=headers, timeout=10, **kwargs)
        item = {'name': name, 'method': method, 'path': path, 'status': response.status_code,
                'content_type': response.headers.get('Content-Type', ''),
                'x_content_type_options': response.headers.get('X-Content-Type-Options'),
                'x_frame_options': response.headers.get('X-Frame-Options'),
                'cors_allow_origin': response.headers.get('Access-Control-Allow-Origin'),
                'csp': response.headers.get('Content-Security-Policy')}
        checks.append(item)
        return response, item

    _, own = probe('order owner', 'GET', '/orders/1', token_a)
    _, other = probe('order IDOR', 'GET', '/orders/1', token_b)
    _, csrf = probe('write without bearer/cross origin', 'POST', '/admin/categories',
                    headers={'Origin': 'https://evil.invalid'}, json={'category_name': 'cross-origin'})
    _, sql = probe('SQLi-shaped product query', 'GET', '/products', params={'keyword': "' OR 1=1--"})
    xss_response, xss = probe('XSS-shaped product query', 'GET', '/products', params={'keyword': '<script>alert(1)</script>'})
    xss['script_reflected'] = '<script>alert(1)</script>' in xss_response.text
    profile_response, profile = probe('bank card profile response', 'GET', '/users/profile', token_a)
    profile['full_card_exposed'] = '6222000000001234' in profile_response.text
    profile['last_four_present'] = '1234' in profile_response.text
    _, before = probe('active bearer', 'GET', '/users/profile', token_a)
    _, logout = probe('logout bearer', 'POST', '/auth/logout', token_a, json={})
    _, after = probe('revoked bearer', 'GET', '/users/profile', token_a)
    _, invalid = probe('invalid bearer', 'GET', '/users/profile', 'not-a-token')
    summary = {'idor_protected': own['status'] == 200 and other['status'] in (403, 404),
               'cross_origin_write_denied': csrf['status'] == 401,
               'sqli_probe_denied': sql['status'] == 400,
               'xss_script_not_reflected': not xss['script_reflected'],
               'logout_revokes_bearer': before['status'] == 200 and logout['status'] == 200 and after['status'] == 401,
               'invalid_bearer_denied': invalid['status'] == 401,
               'bank_card_disclosed': profile['full_card_exposed']}
    output = ROOT / 'docs/evidence/week7'
    output.mkdir(parents=True, exist_ok=True)
    report = {'time_utc': datetime.now(timezone.utc).isoformat(),
              'tool': 'week7_dast.py (requests over actual localhost WSGI HTTP)',
              'environment': 'ephemeral localhost port, in-memory SQLite, fictitious accounts and card; no production mutations',
              'scope': ['SQLi', 'XSS reflection', 'cross-origin unauthenticated write', 'IDOR', 'JWT/logout', 'card disclosure', 'security headers'],
              'checks': checks, 'summary': summary,
              'limit': 'Bounded probes are not a full ZAP/Burp spider or authenticated active scan.'}
    destination = output / f'dast-{label}.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{destination}: {json.dumps(summary, ensure_ascii=False)}')
    return 0 if all(v for k, v in summary.items() if k != 'bank_card_disclosed') else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', choices=('baseline', 'regression'), required=True)
    args = parser.parse_args()
    fixture = CourseSecurityTests()
    fixture.setUp()
    try:
        with SessionLocal.begin() as db:
            db.get(User, 1).bank_card_number = '6222000000001234'
        token_a, token_b = fixture.token(1), fixture.token(2)
        server = make_server('127.0.0.1', 0, get_wsgi_application())
        base = f'http://127.0.0.1:{server.server_port}/api'
        outcome = {}

        def client():
            try:
                outcome['exit'] = scan(base, token_a, token_b, args.label)
            except BaseException as exc:
                outcome['error'] = exc
            finally:
                server.shutdown()

        worker = threading.Thread(target=client, daemon=True)
        worker.start()
        # DB connections were created in this thread, so HTTP is served here too.
        server.serve_forever()
        worker.join(timeout=15)
        server.server_close()
        if 'error' in outcome:
            raise outcome['error']
        return outcome['exit']
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    raise SystemExit(main())
