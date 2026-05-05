import base64
import json
import os
import time
from decimal import Decimal
from typing import Mapping

from django.conf import settings
from gmssl import func, sm2, sm3, sm4


SIGNED_REQUEST_FIELDS = ("order_no", "amount", "merchant_id", "timestamp")


def canonical_string(params: Mapping[str, object], fields: tuple[str, ...] = SIGNED_REQUEST_FIELDS) -> str:
    items = []
    for key in sorted(fields):
        value = params.get(key)
        if value is None or value == "":
            continue
        items.append(f"{key}={value}")
    return "|".join(items)


def sm3_hash_text(text: str) -> str:
    return sm3.sm3_hash(func.bytes_to_list(text.encode("utf-8")))


def public_key_from_private(private_key_hex: str) -> str:
    crypt = sm2.CryptSM2(public_key="", private_key=private_key_hex)
    return crypt._kg(int(private_key_hex, 16), crypt.ecc_table["g"])


def sign_sm2_digest(params: Mapping[str, object], private_key_hex: str) -> str:
    digest_hex = sm3_hash_text(canonical_string(params))
    signer = sm2.CryptSM2(public_key=public_key_from_private(private_key_hex), private_key=private_key_hex)
    return signer.sign(bytes.fromhex(digest_hex), func.random_hex(64))


def verify_sm2_digest(params: Mapping[str, object], public_key_hex: str, signature: str) -> bool:
    if not signature:
        return False
    if len(signature) != 128:
        return False
    digest_hex = sm3_hash_text(canonical_string(params))
    verifier = sm2.CryptSM2(public_key=public_key_hex, private_key="")
    try:
        return bool(verifier.verify(signature, bytes.fromhex(digest_hex)))
    except (TypeError, ValueError):
        return False


def get_merchant_private_key(merchant_id: str) -> str | None:
    return settings.BANK_MERCHANT_PRIVATE_KEYS.get(merchant_id)


def get_merchant_public_key(merchant_id: str) -> str | None:
    return settings.BANK_MERCHANT_PUBLIC_KEYS.get(merchant_id)


def sm2_encrypt_key(key_bytes: bytes, public_key_hex: str) -> str:
    crypt = sm2.CryptSM2(public_key=public_key_hex, private_key="")
    encrypted = crypt.encrypt(key_bytes)
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def sm2_decrypt_key(encrypted_key: str, private_key_hex: str) -> bytes:
    crypt = sm2.CryptSM2(public_key="", private_key=private_key_hex)
    raw = base64.urlsafe_b64decode(encrypted_key.encode("ascii"))
    return crypt.decrypt(raw)


def sm4_encrypt_json(payload: Mapping[str, object], key_bytes: bytes | None = None, iv_bytes: bytes | None = None) -> dict:
    key = key_bytes or os.urandom(16)
    iv = iv_bytes or os.urandom(16)

    def default(value):
        if isinstance(value, Decimal):
            return str(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=default).encode("utf-8")
    crypt = sm4.CryptSM4()
    crypt.set_key(key, sm4.SM4_ENCRYPT)
    data = crypt.crypt_cbc(iv, raw)
    return {
        "key": key,
        "iv": base64.urlsafe_b64encode(iv).decode("ascii"),
        "data": base64.urlsafe_b64encode(data).decode("ascii"),
    }


def sm4_decrypt_json(data: str, iv: str, key_bytes: bytes) -> dict:
    crypt = sm4.CryptSM4()
    crypt.set_key(key_bytes, sm4.SM4_DECRYPT)
    raw = crypt.crypt_cbc(
        base64.urlsafe_b64decode(iv.encode("ascii")),
        base64.urlsafe_b64decode(data.encode("ascii")),
    )
    return json.loads(raw.decode("utf-8"))


def create_result_envelope(payload: Mapping[str, object], recipient_public_key_hex: str) -> dict:
    encrypted = sm4_encrypt_json(payload)
    encrypted_key = sm2_encrypt_key(encrypted["key"], recipient_public_key_hex)
    return {
        "encrypted_key": encrypted_key,
        "iv": encrypted["iv"],
        "data": encrypted["data"],
    }


def open_result_envelope(envelope: Mapping[str, str], recipient_private_key_hex: str) -> dict:
    key = sm2_decrypt_key(envelope["encrypted_key"], recipient_private_key_hex)
    return sm4_decrypt_json(envelope["data"], envelope["iv"], key)


def is_timestamp_fresh(timestamp_value: str, valid_seconds: int | None = None) -> bool:
    try:
        timestamp = int(timestamp_value)
    except (TypeError, ValueError):
        return False
    valid_window = valid_seconds or settings.BANK_PAYMENT_TIMESTAMP_VALID_SECONDS
    return abs(int(time.time()) - timestamp) <= valid_window


def sign_params(params: Mapping[str, object], private_key_hex: str) -> str:
    return sign_sm2_digest(params, private_key_hex)


def verify_params(params: Mapping[str, object], public_key_hex: str, signature: str) -> bool:
    return verify_sm2_digest(params, public_key_hex, signature)
