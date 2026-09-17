"""Isolated SQLite tests. The production database/key files are never used."""
import copy
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from api_service.tests import test_course_security as course
from cryptography.fernet import Fernet
from src.crypto_tunnel import create_key, gcm, unwrap_key, read_key, ROOT
from src.Data_base.models.security import TunnelNonce, AuditEvent


class TunnelTests(unittest.TestCase):
    token = course.CourseSecurityTests.token
    request = course.CourseSecurityTests.request

    def setUp(self):
        course.CourseSecurityTests.setUp(self)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        env = patch.dict(os.environ, {'TUNNEL_KEY_FILE': str(Path(directory.name) / 'server.json'),
                                     'TUNNEL_KEY_ENCRYPTION_KEY': Fernet.generate_key().decode()})
        env.start()
        self.addCleanup(env.stop)
        self.info = {**create_key(), 'v': 1}
        self.info.pop('encrypted_private_key')
        self.auth = self.token(1)
        self.body = {'recipient': '课堂测试', 'phone': '13800001234', 'address': '虚构地址一号'}

    def seal(self, body=None, token=None, path='/api/tunnel/demo', ts=None):
        result = subprocess.run(['node', str(ROOT / 'scripts/seal_tunnel.cjs')], input=json.dumps({
            'body': self.body if body is None else body, 'info': self.info, 'path': path,
            'authorization': 'Bearer ' + (token or self.auth), 'options': {} if ts is None else {'ts': ts}}),
            capture_output=True, text=True, encoding='utf-8', check=True, cwd=ROOT)
        return json.loads(result.stdout)

    def send(self, envelope, token=None, path='/api/tunnel/demo'):
        return self.request(path, envelope, token=token or self.auth)

    def test_rfc8998_vector_and_tag_integrity(self):
        h = bytes.fromhex
        key, nonce, aad = map(h, ('0123456789ABCDEFFEDCBA9876543210', '00001234567800000000ABCD',
                                  'FEEDFACEDEADBEEFFEEDFACEDEADBEEFABADDAD2'))
        plain = h('AAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBCCCCCCCCCCCCCCCCDDDDDDDDDDDDDDDDEEEEEEEEEEEEEEEEFFFFFFFFFFFFFFFFEEEEEEEEEEEEEEEEAAAAAAAAAAAAAAAA')
        expected = h('17F399F08C67D5EE19D0DC9969C4BB7D5FD46FD3756489069157B282BB200735D82710CA5C22F0CCFA7CBF93D496AC15A56834CBCF98C397B4024A2691233B8D')
        ciphertext, tag = gcm(key, nonce, aad).encrypt_and_digest(plain)
        self.assertEqual(ciphertext, expected)
        self.assertEqual(tag.hex(), '83de3541e4c2b58177e065a9bf7b62ec')
        self.assertEqual(gcm(key, nonce, aad).decrypt_and_verify(ciphertext, tag), plain)
        with self.assertRaises(ValueError):
            gcm(key, nonce, b'wrong').decrypt_and_verify(ciphertext, tag)

    def test_browser_interop_and_replay_audit(self):
        envelope = self.seal()
        status, result = self.send(envelope)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['data']['phone_masked'], '138****1234')
        self.assertNotIn(self.body['address'], json.dumps(result, ensure_ascii=False))
        self.assertEqual(self.send(envelope)[0], 409)
        next_envelope = self.seal()
        self.assertNotEqual(envelope['nonce'], next_envelope['nonce'])
        self.assertNotEqual(unwrap_key(envelope['encrypted_key'], read_key()[1]),
                            unwrap_key(next_envelope['encrypted_key'], read_key()[1]))
        self.assertEqual(self.send(next_envelope)[0], 200)
        with course.SessionLocal() as db:
            actions = [event.action for event in db.query(AuditEvent).all()]
            self.assertIn('tunnel.accepted', actions)
            self.assertIn('tunnel.replay', actions)
            self.assertEqual(db.query(TunnelNonce).count(), 2)

    def test_tamper_ciphertext_tag_c3_point_and_metadata(self):
        original = self.seal()
        for field, offset in (('ciphertext', 0), ('tag', 0), ('encrypted_key', 128), ('nonce', 0)):
            changed = copy.deepcopy(original)
            value = changed[field]
            changed[field] = value[:offset] + ('1' if value[offset] == '0' else '0') + value[offset+1:]
            self.assertEqual(self.send(changed)[0], 400, field)
        changed = {**original, 'encrypted_key': '0' * 128 + original['encrypted_key'][128:]}
        self.assertEqual(self.send(changed)[0], 400)
        self.assertEqual(self.send({**original, 'ts': original['ts'] + 1})[0], 400)
        # Rejected tampering must not consume the genuine request's nonce.
        self.assertEqual(self.send(original)[0], 200)

    def test_expiry_future_plaintext_and_size(self):
        for offset in (-125, 125):
            status, data = self.send(self.seal(ts=int(time.time()) + offset))
            self.assertEqual((status, data['code']), (408, 'TUNNEL_EXPIRED'))
        self.assertEqual(self.send(self.body)[0], 400)
        self.assertEqual(self.send({'x': 'a' * 70000})[0], 413)
        self.assertEqual(self.send(self.seal(body=['not an object']))[0], 400)

    def test_authorization_route_binding_and_three_roles(self):
        envelope = self.seal()
        self.assertEqual(self.request('/api/tunnel/demo', envelope)[0], 401)
        admin, auditor = self.token(3), self.token(4)
        self.assertEqual(self.send(envelope, token=admin)[0], 400)
        self.assertEqual(self.send(self.seal(token=admin), token=admin)[0], 200)
        self.assertEqual(self.send(self.seal(token=auditor), token=auditor)[0], 403)
        self.assertEqual(self.send(envelope, path='/api/users/bank-card')[0], 400)
        self.assertEqual(self.client.get('/api/tunnel/key').status_code, 200)

    def test_bank_card_only_mutates_after_valid_tunnel(self):
        path = '/api/users/bank-card'
        body = {'bank_card_number': '6222000000001234'}
        self.assertEqual(self.send(body, path=path)[0], 400)
        with patch('api_service.api.views.UserCache.invalidate_user_caches'):
            envelope = self.seal(body=body, path=path)
            status, data = self.send(envelope, path=path)
            self.assertEqual(status, 200, data)
            self.assertEqual(self.send(envelope, path=path)[0], 409)
        with course.SessionLocal() as db:
            self.assertEqual(db.get(course.User, 1).bank_card_number, body['bank_card_number'])

    def test_missing_key_fails_closed(self):
        envelope = self.seal()
        changed_kid = ('0' if envelope['kid'][0] != '0' else '1') + envelope['kid'][1:]
        status, data = self.send({**envelope, 'kid': changed_kid})
        self.assertEqual((status, data['code']), (400, 'TUNNEL_KEY_CHANGED'))
        with patch.dict(os.environ, {'TUNNEL_KEY_FILE': str(ROOT / 'keys/does-not-exist.json')}):
            self.assertEqual(self.send(envelope)[0], 503)


if __name__ == '__main__':
    unittest.main()
