"""SM2 adapter using OS-backed randomness and authenticated ciphertext decoding.

Wire format and curve operations interoperate with gmssl 3.2.2. Its default
random_hex uses random.choice, and its decrypt does not compare C3; neither
default is suitable for application key generation or authenticated decryption.
"""
import secrets

from gmssl import sm2, sm3


def secure_scalar(private=False):
    n = int(sm2.default_ecc_table['n'], 16)
    return f'{secrets.randbelow(n - (2 if private else 1)) + 1:064x}'


class SecureSM2(sm2.CryptSM2):
    def __init__(self, private_key, public_key, **kwargs):
        # Strip only the exact optional uncompressed-point prefix, never lstrip.
        if len(public_key) == 130 and public_key.startswith('04'):
            public_key = public_key[2:]
        super().__init__(private_key=private_key, public_key='', **kwargs)
        if public_key:
            self._validate_point(public_key)
        self.public_key = public_key

    def _validate_point(self, point):
        if len(point) != 2 * self.para_len:
            raise ValueError('Invalid SM2 point length')
        x, y = int(point[:self.para_len], 16), int(point[self.para_len:], 16)
        p, a, b = (int(self.ecc_table[name], 16) for name in ('p', 'a', 'b'))
        if not (0 <= x < p and 0 <= y < p) or (y * y - x * x * x - a * x - b) % p:
            raise ValueError('Invalid SM2 curve point')

    def sign_with_sm3(self, data, random_hex_str=None):
        return super().sign_with_sm3(data, random_hex_str or secure_scalar())

    def encrypt(self, data):
        if not data:
            raise ValueError('SM2 plaintext must not be empty')
        self._validate_point(self.public_key)
        while True:
            k = int(secure_scalar(), 16)
            c1 = self._kg(k, self.ecc_table['g'])
            xy = self._kg(k, self.public_key)
            mask = bytes.fromhex(sm3.sm3_kdf(xy.encode('ascii'), len(data)))
            if any(mask):
                break
        c2 = bytes(a ^ b for a, b in zip(data, mask))
        x, y = bytes.fromhex(xy[:self.para_len]), bytes.fromhex(xy[self.para_len:])
        c3 = bytes.fromhex(sm3.sm3_hash(list(x + data + y)))
        return bytes.fromhex(c1) + (c3 + c2 if self.mode else c2 + c3)

    def decrypt(self, data):
        point_size = self.para_len
        if len(data) <= point_size + 32:
            raise ValueError('Invalid SM2 ciphertext length')
        c1 = data[:point_size].hex()
        self._validate_point(c1)
        if self.mode:
            c3, c2 = data[point_size:point_size + 32], data[point_size + 32:]
        else:
            c2, c3 = data[point_size:-32], data[-32:]
        xy = self._kg(int(self.private_key, 16), c1)
        mask = bytes.fromhex(sm3.sm3_kdf(xy.encode('ascii'), len(c2)))
        if not any(mask):
            raise ValueError('Invalid SM2 KDF output')
        plaintext = bytes(a ^ b for a, b in zip(c2, mask))
        x, y = bytes.fromhex(xy[:self.para_len]), bytes.fromhex(xy[self.para_len:])
        expected = bytes.fromhex(sm3.sm3_hash(list(x + plaintext + y)))
        if not secrets.compare_digest(c3, expected):
            raise ValueError('SM2 authentication failed')
        return plaintext
