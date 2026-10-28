"""Windows API: localhost plus the assigned WSL adapter, never all interfaces."""
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'api_service'))
sys.path.insert(0, str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service.settings')


def wsl_addresses():
    command = "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*WSL*' } | Select-Object -ExpandProperty IPAddress | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            check=True, capture_output=True, text=True)
    addresses = json.loads(result.stdout.strip() or '[]')
    if isinstance(addresses, str):
        addresses = [addresses]
    if not addresses:
        raise RuntimeError('WSL adapter not found. Start WSL before starting the backend.')
    for address in addresses:
        parsed = ipaddress.IPv4Address(address)
        if not parsed.is_private or parsed.is_unspecified or parsed.is_loopback:
            raise RuntimeError('Unexpected WSL adapter address')
    return addresses


if __name__ == '__main__':
    from django.core.wsgi import get_wsgi_application
    from waitress import serve
    listeners = ['127.0.0.1:8080'] + [f'{address}:8080' for address in wsl_addresses()]
    application = get_wsgi_application()
    print('API listeners: ' + ', '.join(listeners), flush=True)
    # The application validates X-MTLS-PROXY-SECRET before using X-Forwarded-Proto.
    # Waitress must preserve that header, but must not itself trust any proxy.
    serve(application, listen=' '.join(listeners), threads=4, trusted_proxy=None,
          clear_untrusted_proxy_headers=False, max_request_body_size=2 * 1024 * 1024)
