"""Create reusable local TLS material and a WSL nginx site. Never replace existing keys."""
import argparse
import ipaddress
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--backend-ip', required=True)
args = parser.parse_args()
ipaddress.IPv4Address(args.backend_ip)
out = root / 'keys' / 'mtls_local'
out.mkdir(parents=True, exist_ok=True)
now = datetime.now(timezone.utc)

def key_for(name):
    path = out / f'{name}.key'
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return key

ca_key = key_for('classroom-ca')
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Secondhand Classroom Local CA')])
ca_path = out / 'classroom-ca.crt'
def needs_certificate(path):
    if not path.exists():
        return True
    try:
        x509.load_pem_x509_certificate(path.read_bytes()).extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
        return False
    except x509.ExtensionNotFound:
        return True

if needs_certificate(ca_path):
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=1825))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .sign(ca_key, hashes.SHA256()))
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
ca = x509.load_pem_x509_certificate(ca_path.read_bytes())

for name in ('localhost', 'week1_admin', 'week1_auditor', 'week1_buyer'):
    key = key_for(name)
    path = out / f'{name}.crt'
    renewed = needs_certificate(path)
    if renewed:
        builder = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
                   .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=365))
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
                   .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if name == 'localhost' else ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False))
        if name == 'localhost':
            builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        cert = builder.sign(ca_key, hashes.SHA256())
        path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    if name != 'localhost' and (renewed or not (out / f'{name}.p12').exists()):
        password_path = out / f'{name}.import-password.txt'
        password = password_path.read_text(encoding='utf-8') if password_path.exists() else secrets.token_urlsafe(18)
        cert = x509.load_pem_x509_certificate(path.read_bytes())
        (out / f'{name}.p12').write_bytes(pkcs12.serialize_key_and_certificates(name.encode(), key, cert, [ca], serialization.BestAvailableEncryption(password.encode())))
        (out / f'{name}.import-password.txt').write_text(password, encoding='utf-8')

secret = dotenv_values(root / '.env').get('MTLS_PROXY_SECRET', '')
if not re.fullmatch(r'[A-Za-z0-9_-]{32,}', secret):
    raise SystemExit('MTLS_PROXY_SECRET must be configured as a URL-safe random secret (>=32 chars).')
(out / 'proxy-secret.conf').write_text(f'proxy_set_header X-MTLS-PROXY-SECRET "{secret}";\n', encoding='utf-8')
linux_root = '/mnt/' + root.drive[0].lower() + root.as_posix()[2:]
site = '''# Included from nginx http {}; generated for the local WSL classroom.
server {
    listen 8443 ssl;
    server_name localhost;
    ssl_certificate __ROOT__/keys/mtls_local/localhost.crt;
    ssl_certificate_key __ROOT__/keys/mtls_local/localhost.key;
    ssl_client_certificate __ROOT__/keys/mtls_local/classroom-ca.crt;
    ssl_verify_client optional;
    ssl_verify_depth 2;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_tickets off;
    root __ROOT__/frontend/dist;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
    location /api/ {
        proxy_pass http://__IP__:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-SSL-CLIENT-VERIFY $ssl_client_verify;
        proxy_set_header X-SSL-CLIENT-CERT $ssl_client_escaped_cert;
        proxy_set_header X-SSL-CLIENT-S-DN $ssl_client_s_dn;
        proxy_set_header X-CLIENT-CERT-PEM "";
        include /etc/nginx/snippets/secondhand-mtls-secret.conf;
    }
}
'''.replace('__ROOT__', linux_root).replace('__IP__', args.backend_ip)
(out / 'nginx-site.conf').write_text(site, encoding='utf-8')
print('TLS material prepared in keys/mtls_local (existing CA and client keys preserved).')
print('Client import passwords are in the matching *.import-password.txt files; values not printed.')
