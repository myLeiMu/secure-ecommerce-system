"""Generate missing local keys and replace an insufficiently long JWT key."""
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import dotenv_values, set_key

root = Path(__file__).resolve().parents[1]
path = root / '.env'
config = dotenv_values(path)
values = {'MTLS_PROXY_SECRET': secrets.token_urlsafe(48), 'MFA_ENCRYPTION_KEY': Fernet.generate_key().decode(),
          'JWT_SECRET_KEY': secrets.token_urlsafe(48)}
path.touch(exist_ok=True)
for name, val in values.items():
    if not config.get(name) or (name == 'JWT_SECRET_KEY' and len(config[name]) < 32):
        set_key(str(path), name, val)
        print(f'Configured {name} (value hidden)')
print('Keep .env private and include it in an encrypted backup.')
