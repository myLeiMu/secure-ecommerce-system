"""Rotate the LOCAL classroom merchant pair together; never print private material.

Stop both payment services before running, then restart both. Existing encrypted
callbacks need the old private key, so finish pending payments first.
"""
import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values, set_key
from gmssl import sm2

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rotate', action='store_true', required=True)
    parser.parse_args()
    env = ROOT / '.env'
    values = dotenv_values(env)
    merchant = values.get('ECOMMERCE_MERCHANT_ID') or 'ECOMMERCE_DEMO'
    # Preserve other merchants' configured pairs.
    def mapping(name):
        return dict(item.split(':', 1) for item in (values.get(name) or '').split(',') if ':' in item)
    private_map = mapping('BANK_MERCHANT_PRIVATE_KEYS')
    public_map = mapping('BANK_MERCHANT_PUBLIC_KEYS')
    private = f'{secrets.randbelow(int(sm2.default_ecc_table["n"], 16) - 1) + 1:064x}'
    signer = sm2.CryptSM2(public_key='', private_key=private)
    public = signer._kg(int(private, 16), sm2.default_ecc_table['g'])
    private_map[merchant], public_map[merchant] = private, public
    backup = ROOT / 'keys/payment-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ.env')
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(env.read_bytes())
    set_key(str(env), 'ECOMMERCE_MERCHANT_PRIVATE_KEY', private)
    set_key(str(env), 'BANK_MERCHANT_PRIVATE_KEYS', ','.join(f'{k}:{v}' for k, v in private_map.items()))
    set_key(str(env), 'BANK_MERCHANT_PUBLIC_KEYS', ','.join(f'{k}:{v}' for k, v in public_map.items()))
    report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'merchant': merchant,
              'rotated_together': True, 'public_key': public,
              'restart_both_services_required': True, 'old_env_backup': 'keys/payment-backups (gitignored)'}
    output = ROOT / 'docs/evidence/week8/payment-key-rotation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Merchant pair rotated together in local .env; restart both services. No private values printed.')


if __name__ == '__main__':
    main()
