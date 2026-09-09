"""Disposable UI integration fixture on localhost:8765; never touches MySQL.

Fixture accounts user1..user5 / TestPass123! (user3 admin, user4 auditor).
Bank payments are not part of this preview. Stop the process to discard data.
"""
import mimetypes
import sys
from pathlib import Path
from urllib.parse import unquote
from wsgiref.simple_server import make_server

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from api_service.tests.test_course_security import CourseSecurityTests
from django.core.wsgi import get_wsgi_application

CourseSecurityTests().setUp()
application = get_wsgi_application()
dist = (root / 'frontend' / 'dist').resolve()


def serve(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    if path.startswith('/api/'):
        return application(environ, start_response)
    target = (dist / unquote(path).lstrip('/')).resolve()
    if not target.is_relative_to(dist):
        start_response('403 Forbidden', [])
        return [b'Forbidden']
    if not target.is_file():
        target = dist / 'index.html'
    content = target.read_bytes()
    start_response('200 OK', [('Content-Type', mimetypes.guess_type(target)[0] or 'application/octet-stream'),
                              ('Content-Length', str(len(content)))])
    return [content]


if __name__ == '__main__':
    print('Disposable integration preview: http://127.0.0.1:8765', flush=True)
    with make_server('127.0.0.1', 8765, serve) as server:
        server.serve_forever()
