import base64
import json

from gmssl import func, sm2, sm3, sm4


SIGNED_REQUEST_FIELDS = ("order_no", "amount", "merchant_id", "timestamp")


def canonical_string(params: dict, fields: tuple[str, ...] = SIGNED_REQUEST_FIELDS) -> str:
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


def sign_payment_params(params: dict, private_key_hex: str) -> str:
    digest_hex = sm3_hash_text(canonical_string(params))
    signer = sm2.CryptSM2(public_key=public_key_from_private(private_key_hex), private_key=private_key_hex)
    return signer.sign(bytes.fromhex(digest_hex), func.random_hex(64))


def sm2_decrypt_key(encrypted_key: str, private_key_hex: str) -> bytes:
    crypt = sm2.CryptSM2(public_key="", private_key=private_key_hex)
    raw = base64.urlsafe_b64decode(encrypted_key.encode("ascii"))
    return crypt.decrypt(raw)


def sm4_decrypt_json(data: str, iv: str, key_bytes: bytes) -> dict:
    crypt = sm4.CryptSM4()
    crypt.set_key(key_bytes, sm4.SM4_DECRYPT)
    raw = crypt.crypt_cbc(
        base64.urlsafe_b64decode(iv.encode("ascii")),
        base64.urlsafe_b64decode(data.encode("ascii")),
    )
    return json.loads(raw.decode("utf-8"))


def open_result_envelope(encrypted_key: str, iv: str, data: str, private_key_hex: str) -> dict:
    key = sm2_decrypt_key(encrypted_key, private_key_hex)
    return sm4_decrypt_json(data, iv, key)
