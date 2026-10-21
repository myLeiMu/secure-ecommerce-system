"""One-time/idempotent card migration. Never prints keys or account numbers."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
from sqlalchemy import inspect, text

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
load_dotenv(root / '.env')
if not os.getenv('BANK_CARD_ENCRYPTION_KEY'):
    key = Fernet.generate_key().decode('ascii')
    set_key(root / '.env', 'BANK_CARD_ENCRYPTION_KEY', key)
    os.environ['BANK_CARD_ENCRYPTION_KEY'] = key

from src.Data_base.database import engine
from src.Data_base.encrypted_fields import PREFIX, card_cipher, encrypt_card, decrypt_card

cipher = card_cipher()  # Validate key before touching schema or data.
with engine.connect() as connection:
    rows = connection.execute(text('SELECT user_id, bank_card_number FROM users WHERE bank_card_number IS NOT NULL')).all()
legacy = [(uid, card) for uid, card in rows if card and not card.startswith(PREFIX)]
# Validate the existing key on already migrated rows before proceeding.
for _, card in rows:
    if card and card.startswith(PREFIX):
        decrypt_card(card)
if legacy:
    backup = root / 'keys' / 'card-migration-backups'
    backup.mkdir(parents=True, exist_ok=True)
    destination = backup / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json.enc')
    destination.write_bytes(cipher.encrypt(json.dumps(legacy).encode('utf-8')))
columns = {column['name']: column for column in inspect(engine).get_columns('users')}
if engine.dialect.name == 'mysql' and getattr(columns['bank_card_number']['type'], 'length', 0) < 512:
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE users MODIFY COLUMN bank_card_number VARCHAR(512) NULL DEFAULT NULL'))
with engine.begin() as connection:
    for uid, original in legacy:
        encrypted = encrypt_card(original)
        assert decrypt_card(encrypted) == original
        result = connection.execute(text('UPDATE users SET bank_card_number=:encrypted WHERE user_id=:uid AND bank_card_number=:original'),
                                    {'encrypted': encrypted, 'uid': uid, 'original': original})
        if result.rowcount != 1:
            raise RuntimeError('Concurrent card update detected; migration rolled back, retry while services are stopped')
    remaining = connection.execute(text("SELECT COUNT(*) FROM users WHERE bank_card_number IS NOT NULL AND bank_card_number != '' AND bank_card_number NOT LIKE 'enc:v1:%'")).scalar_one()
    if remaining:
        raise RuntimeError('Unencrypted rows remain; migration rolled back')
print(json.dumps({'migrated_rows': len(legacy), 'plaintext_rows_remaining': remaining,
                  'backup_encrypted': bool(legacy), 'key_in_environment_only': True}))
