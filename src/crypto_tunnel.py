"""Week 4 envelope primitives. No plaintext/private keys are logged here."""
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from gmssl import sm2, sm3

ROOT = Path(__file__).resolve().parents[1]
WINDOW = 120
MAX_PLAINTEXT = 32768
PROTECTED = {('POST', '/api/tunnel/demo'), ('POST', '/api/users/bank-card')}


class _SM4GCM:
    """Public cryptography API; plaintext is returned only after tag validation.

    cryptography 50/OpenSSL supports SM4-GCM natively. Older unsupported builds
    fail closed; there is no weaker cipher or unauthenticated fallback.
    """
    def __init__(self, key, nonce, aad):
        self.key, self.nonce, self.aad = key, nonce, aad

    def encrypt_and_digest(self, plaintext):
        encryptor = Cipher(algorithms.SM4(self.key), modes.GCM(self.nonce)).encryptor()
        encryptor.authenticate_additional_data(self.aad)
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return ciphertext, encryptor.tag

    def decrypt_and_verify(self, ciphertext, tag):
        if len(tag) != 16:
            raise ValueError('Invalid GCM tag length')
        decryptor = Cipher(algorithms.SM4(self.key), modes.GCM(self.nonce, tag)).decryptor()
        decryptor.authenticate_additional_data(self.aad)
        try:
            return decryptor.update(ciphertext) + decryptor.finalize()
        except InvalidTag as exc:
            raise ValueError('Invalid GCM tag') from exc


def gcm(key, nonce, aad):
    if len(key) != 16 or len(nonce) != 12:
        raise ValueError('Invalid key/nonce size')
    return _SM4GCM(key, nonce, aad)


def key_path():
    return Path(os.environ.get('TUNNEL_KEY_FILE', str(ROOT / 'keys/tunnel/server.json')))


def read_key():
    record = json.loads(key_path().read_text(encoding='utf-8'))
    private = Fernet(os.environ['TUNNEL_KEY_ENCRYPTION_KEY'].encode()).decrypt(record['encrypted_private_key'].encode()).decode()
    return record, private


def create_key():
    private = '%064x' % (secrets.randbelow(int(sm2.default_ecc_table['n'], 16) - 1) + 1)
    crypt = sm2.CryptSM2(private_key=private, public_key='', mode=1)
    public = crypt._kg(int(private, 16), sm2.default_ecc_table['g'])
    record = {'kid': hashlib.sha256(bytes.fromhex(public)).hexdigest()[:16], 'public_key': '04' + public,
              'encrypted_private_key': Fernet(os.environ['TUNNEL_KEY_ENCRYPTION_KEY'].encode()).encrypt(private.encode()).decode()}
    path = key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never silently rotate/overwrite a key used by running clients.
    with path.open('x', encoding='utf-8') as out:
        json.dump(record, out, indent=2)
    return record


def unwrap_key(encoded, private):
    raw = bytes.fromhex(encoded)
    if len(raw) != 112:
        raise ValueError('Invalid envelope')
    point = raw[:64].hex()
    x, y = int(point[:64], 16), int(point[64:], 16)
    curve = sm2.default_ecc_table
    p, a, b = (int(curve[k], 16) for k in ('p', 'a', 'b'))
    if not (0 <= x < p and 0 <= y < p) or (y*y - x*x*x - a*x - b) % p:
        raise ValueError('Invalid envelope')
    crypt = sm2.CryptSM2(private_key=private, public_key='', mode=1)
    shared = bytes.fromhex(crypt._kg(int(private, 16), point))
    key = crypt.decrypt(raw)
    # gmssl 3.2.2 decrypt does not verify C3; do it explicitly before use.
    expected = bytes.fromhex(sm3.sm3_hash(list(shared[:32] + key + shared[32:])))
    if len(key) != 16 or not hmac.compare_digest(raw[64:96], expected):
        raise ValueError('Invalid envelope')
    return key


def associated_data(envelope, method, path, authorization):
    token_hash = hashlib.sha256(authorization.encode('utf-8')).hexdigest()
    return '\n'.join((str(envelope['v']), envelope['kid'], method.upper(), path,
                      str(envelope['ts']), envelope['nonce'], token_hash)).encode('utf-8')
