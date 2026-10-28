"""Disposable UI integration fixture on localhost:8765; never touches MySQL.

Fixture accounts user1..user5 / TestPass123! (user3 admin, user4 auditor).
Bank payments are not part of this preview. Stop the process to discard data.
"""
import mimetypes
import argparse
import ssl
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
    start_response('200 OK', [('Content-Security-Policy', "default-src 'none'; script-src 'self'; script-src-attr 'none'; style-src 'self'; style-src-attr 'none'; img-src 'self' https: http: data: blob:; font-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"),
                              ('X-Frame-Options', 'DENY'), ('X-Content-Type-Options', 'nosniff'),
                              ('Content-Type', mimetypes.guess_type(target)[0] or 'application/octet-stream'),
                              ('Content-Length', str(len(content)))])
    return [content]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--https', action='store_true')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    print(f'Disposable integration preview: {"https" if args.https else "http"}://127.0.0.1:{args.port}', flush=True)
    with make_server('127.0.0.1', args.port, serve) as server:
        if args.https:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(root / 'keys/mtls_local/localhost.crt', root / 'keys/mtls_local/localhost.key')
            server.socket = context.wrap_socket(server.socket, server_side=True)
        server.serve_forever()
