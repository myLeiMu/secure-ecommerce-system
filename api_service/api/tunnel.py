"""Authenticated, replay-protected application request envelopes (HTTPS required)."""
import hashlib
import io
import json
import re
import time

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.crypto_tunnel import (PROTECTED, WINDOW, MAX_PLAINTEXT, read_key, unwrap_key,
                               associated_data, gcm)
from src.Data_base.database import SessionLocal
from src.Data_base.models.security import TunnelNonce
from .security_core import audit


class TunnelMiddleware(MiddlewareMixin):
    def reject(self, request, status, code, message):
        with SessionLocal.begin() as db:
            audit(db, request, 'tunnel.' + code.removeprefix('TUNNEL_').lower(), result='denied')
        return JsonResponse({'code': code, 'message': message, 'data': None}, status=status)

    def process_request(self, request):
        if (request.method, request.path.rstrip('/')) not in PROTECTED:
            return None
        if not getattr(request, 'user_info', None):
            return JsonResponse({'code': 401, 'message': '请先登录', 'data': None}, status=401)
        try:
            if len(request.body) > MAX_PLAINTEXT * 2 + 2048:
                return self.reject(request, 413, 'TUNNEL_TOO_LARGE', '加密请求过大')
            envelope = json.loads(request.body)
            fields = {'v', 'kid', 'ts', 'nonce', 'encrypted_key', 'ciphertext', 'tag'}
            if not isinstance(envelope, dict) or set(envelope) != fields:
                return self.reject(request, 400, 'TUNNEL_REQUIRED', '此接口必须使用加密请求')
            if type(envelope['v']) is not int or envelope['v'] != 1 or type(envelope['ts']) is not int:
                raise ValueError()
            for name, size in (('kid', 16), ('nonce', 24), ('encrypted_key', 224), ('tag', 32)):
                if not isinstance(envelope[name], str) or not re.fullmatch('[0-9a-f]{%d}' % size, envelope[name]):
                    raise ValueError()
            ciphertext = envelope['ciphertext']
            if not isinstance(ciphertext, str) or len(ciphertext) > MAX_PLAINTEXT * 2 or not re.fullmatch('(?:[0-9a-f]{2})+', ciphertext):
                raise ValueError()
            now = int(time.time())
            if abs(now - envelope['ts']) > WINDOW:
                return self.reject(request, 408, 'TUNNEL_EXPIRED', '请求超出 120 秒时间窗口，请重新提交')
        except (ValueError, TypeError, UnicodeError):
            return self.reject(request, 400, 'TUNNEL_INVALID', '加密请求格式不正确')
        try:
            record, private = read_key()
        except Exception:
            return self.reject(request, 503, 'TUNNEL_UNAVAILABLE', '安全通道未配置，请联系管理员')
        try:
            if envelope['kid'] != record['kid']:
                return self.reject(request, 400, 'TUNNEL_KEY_CHANGED', '通道密钥已更新，请重新提交')
            key = unwrap_key(envelope['encrypted_key'], private)
            cipher = gcm(key, bytes.fromhex(envelope['nonce']), associated_data(
                envelope, request.method, request.path, request.META.get('HTTP_AUTHORIZATION', '')))
            plaintext = cipher.decrypt_and_verify(bytes.fromhex(ciphertext), bytes.fromhex(envelope['tag']))
            data = json.loads(plaintext)
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, TypeError, UnicodeError):
            return self.reject(request, 400, 'TUNNEL_INVALID', '加密请求验证失败')
        nonce_hash = hashlib.sha256((record['kid'] + ':' + envelope['nonce']).encode()).hexdigest()
        try:
            with SessionLocal.begin() as db:
                db.query(TunnelNonce).filter(TunnelNonce.expires_at < now).delete(synchronize_session=False)
                db.add(TunnelNonce(nonce_hash=nonce_hash, expires_at=envelope['ts'] + WINDOW + 1))
                db.flush()  # Unique primary key atomically rejects concurrent duplicates.
                audit(db, request, 'tunnel.accepted')
        except IntegrityError:
            return self.reject(request, 409, 'TUNNEL_REPLAY', '检测到重复请求，请重新提交')
        except SQLAlchemyError:
            return JsonResponse({'code': 'TUNNEL_UNAVAILABLE', 'message': '防重放存储不可用', 'data': None}, status=503)
        request._body = plaintext
        request._stream = io.BytesIO(plaintext)
        request.META['CONTENT_LENGTH'] = str(len(plaintext))
        request.META['CONTENT_TYPE'] = 'application/json'
        request.content_type = 'application/json'
        request.tunnel_verified = True
        return None


class TunnelKeyView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            record, _ = read_key()
        except Exception:
            return Response({'code': 'TUNNEL_UNAVAILABLE', 'message': '请先初始化安全通道', 'data': None}, status=503)
        response = Response({'code': 200, 'data': {'v': 1, 'kid': record['kid'],
                            'public_key': record['public_key'], 'window_seconds': WINDOW}})
        response['Cache-Control'] = 'no-store'
        return response


class TunnelDemoView(APIView):
    def post(self, request):
        data = request.data
        if not all(isinstance(data.get(k), str) and 0 < len(data[k]) <= 200 for k in ('recipient', 'phone', 'address')):
            return Response({'code': 400, 'message': '请填写收件人、手机号和地址（各不超过 200 字）'}, status=400)
        phone = data['phone']
        return Response({'code': 200, 'message': '密文验证通过，收件信息已解密（演示不保存）', 'data': {
            'verified': True, 'phone_masked': phone[:3] + '****' + phone[-4:],
            'plaintext_sha256': hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                                        separators=(',', ':')).encode()).hexdigest()}})
