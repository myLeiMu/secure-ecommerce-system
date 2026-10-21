import unittest
from unittest.mock import patch

from gmssl import sm2
from src.utils.secure_sm2 import SecureSM2, secure_scalar


class SecureSM2Tests(unittest.TestCase):
    def test_encrypt_sign_interoperate_without_legacy_random_generator(self):
        private = secure_scalar(private=True)
        curve = SecureSM2(private_key=private, public_key='')
        public = curve._kg(int(private, 16), curve.ecc_table['g'])
        for mode in (0, 1):
            crypt = SecureSM2(private_key=private, public_key='04' + public, mode=mode)
            legacy = sm2.CryptSM2(private_key=private, public_key='', mode=mode)
            legacy.public_key = public
            with patch('gmssl.func.random_hex', side_effect=AssertionError('Insecure PRNG called')):
                encrypted = crypt.encrypt(b'payment-key-interoperability')
                self.assertEqual(crypt.decrypt(encrypted), b'payment-key-interoperability')
                self.assertEqual(legacy.decrypt(encrypted), b'payment-key-interoperability')
                signature = crypt.sign_with_sm3(b'signed-message')
                self.assertTrue(legacy.verify_with_sm3(signature, b'signed-message'))
                self.assertFalse(legacy.verify_with_sm3(signature, b'tampered-message'))
            for offset in (0, 65, len(encrypted) - 1):
                tampered = bytearray(encrypted)
                tampered[offset] ^= 1
                with self.assertRaises(ValueError):
                    crypt.decrypt(bytes(tampered))

    def test_curve_rejects_invalid_points(self):
        with self.assertRaises(ValueError):
            SecureSM2(private_key='', public_key='00' * 64)
