"""Verify current local paired merchant configuration, emitting booleans only."""
import json
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bank_service.payments.security import verify_params, create_result_envelope
from api_service.api.payment_crypto import sign_payment_params, public_key_from_private, open_result_envelope

values = dotenv_values(ROOT / '.env')
merchant = values.get('ECOMMERCE_MERCHANT_ID') or 'ECOMMERCE_DEMO'
private = values['ECOMMERCE_MERCHANT_PRIVATE_KEY']
public_map = dict(item.split(':', 1) for item in values['BANK_MERCHANT_PUBLIC_KEYS'].split(','))
private_map = dict(item.split(':', 1) for item in values['BANK_MERCHANT_PRIVATE_KEYS'].split(','))
params = {'merchant_id': merchant, 'order_no': 'W8-OFFLINE-PAIR-CHECK', 'amount': '1.00', 'timestamp': str(int(time.time()))}
signature = sign_payment_params(params, private)
payload = {'order_no': params['order_no'], 'status': 'SUCCESS', 'nonce': secrets.token_hex(16)}
envelope = create_result_envelope(payload, public_map[merchant])
checks = {'public_matches_private': public_key_from_private(private) == public_map[merchant],
          'both_local_services_same_merchant_private': private == private_map[merchant],
          'ecommerce_signature_bank_verifies': verify_params(params, public_map[merchant], signature),
          'bank_envelope_ecommerce_decrypts': open_result_envelope(envelope['encrypted_key'], envelope['iv'], envelope['data'], private) == payload,
          'modified_amount_rejected': not verify_params({**params, 'amount': '2.00'}, public_map[merchant], signature)}
out = ROOT / 'docs/evidence/week8/payment-pair-check.json'
out.write_text(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
                          'scope': 'Offline crypto interoperability using local rotated pair; no real order/payment written.'}, indent=2), encoding='utf-8')
print('Payment pair checks:', checks)
raise SystemExit(0 if all(checks.values()) else 1)
