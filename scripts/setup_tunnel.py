"""Idempotent local setup: dedicated encrypted SM2 key and nonce table only."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv(ROOT / '.env')
from src.crypto_tunnel import create_key, read_key, key_path

if not os.environ.get('TUNNEL_KEY_ENCRYPTION_KEY'):
    if key_path().exists():
        raise SystemExit('Existing key requires its original TUNNEL_KEY_ENCRYPTION_KEY; restore it first.')
    master = Fernet.generate_key().decode()
    with (ROOT / '.env').open('a', encoding='utf-8') as out:
        out.write('\nTUNNEL_KEY_ENCRYPTION_KEY=' + master + '\n')
    os.environ['TUNNEL_KEY_ENCRYPTION_KEY'] = master
record = read_key()[0] if key_path().exists() else create_key()
from src.Data_base.database import engine
from src.Data_base.models.security import TunnelNonce
TunnelNonce.__table__.create(engine, checkfirst=True)
print('Tunnel ready; kid=' + record['kid'] + '; private key encrypted; nonce table ready.')
