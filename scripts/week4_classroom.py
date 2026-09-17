"""Repeatable classroom evidence and optional isolated localhost preview."""
import argparse
import io
import json
import mimetypes
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_service.tests.test_tunnel import TunnelTests
from api_service.tests import test_course_security


def audit_rows(case):
    with test_course_security.SessionLocal() as db:
        return [{'case': case, 'action': e.action, 'resource': e.resource, 'result': e.result,
                 'role': e.role, 'username': e.username, 'created_at': e.created_at.isoformat()}
                for e in db.query(test_course_security.AuditEvent).order_by(test_course_security.AuditEvent.event_id)]


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_records = []

    def stopTest(self, test):
        self.audit_records.extend(audit_rows(test.id()))
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'docs/evidence/week4'
    output.mkdir(parents=True, exist_ok=True)
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(TunnelTests),
                              unittest.defaultTestLoader.loadTestsFromModule(test_course_security)])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=EvidenceResult).run(suite)
    output.joinpath('tests.txt').write_text(stream.getvalue(), encoding='utf-8')
    output.joinpath('results.json').write_text(json.dumps({
        'time_utc': datetime.now(timezone.utc).isoformat(),
        'environment': 'Isolated SQLite; Node uses exact browser encryption module; real SM2/SM4-GCM',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'passed': result.wasSuccessful()}, indent=2), encoding='utf-8')
    if not result.wasSuccessful():
        print(stream.getvalue())
        return 1
    # Fill audit dictionary examples using real endpoints in a fresh isolated fixture.
    extra = test_course_security.CourseSecurityTests()
    extra.setUp()
    try:
        cases = [('/api/auth/login', {'username': 'user1', 'password': 'TestPass123!'}, None, 200),
                 ('/api/auth/login', {'username': 'user1', 'password': 'incorrect'}, None, 401),
                 ('/api/admin/categories', {'category_name': '课堂审计样例分类'}, 3, 200),
                 ('/api/auth/mfa/rebind', {'code': None}, 3, 400)]
        for path, body, uid, expected in cases:
            status, _ = extra.request(path, body, uid=uid)
            if status != expected:
                raise AssertionError(f'Audit example {path}: expected {expected}, got {status}')
        result.audit_records.extend(audit_rows('audit dictionary supplemental endpoint checks'))
    finally:
        extra.doCleanups()
    output.joinpath('audit-examples.json').write_text(json.dumps({
        'environment': 'Isolated SQLite; collected from actual middleware/views, no inserted fake audit events',
        'events': result.audit_records}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS: {result.testsRun} tests; reports: {output}')
    if not args.serve:
        return 0
    fixture = TunnelTests()
    try:
        fixture.setUp()
        from django.core.wsgi import get_wsgi_application
        from wsgiref.simple_server import make_server
        application = get_wsgi_application()
        dist = (ROOT / 'frontend/dist').resolve()

        def app(environ, start_response):
            if environ.get('PATH_INFO', '').startswith('/api/'):
                return application(environ, start_response)
            candidate = (dist / environ.get('PATH_INFO', '').lstrip('/')).resolve()
            if not candidate.is_relative_to(dist) or not candidate.is_file():
                candidate = dist / 'index.html'
            body = candidate.read_bytes()
            start_response('200 OK', [('Content-Type', mimetypes.guess_type(str(candidate))[0] or 'application/octet-stream'),
                                      ('Content-Length', str(len(body)))])
            return [body]

        print('Isolated demo: http://127.0.0.1:8767/tunnel-demo ; user1 / TestPass123!', flush=True)
        with make_server('127.0.0.1', 8767, app) as server:
            server.serve_forever()
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    raise SystemExit(main())
