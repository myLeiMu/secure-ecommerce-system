import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from urllib.parse import quote
from cryptography.fernet import Fernet
from src.authentication import JWTUtils
from src.Data_base.models.security import SecurityState, LoginChallenge, AuditEvent

ROLES = ('normal', 'merchant', 'admin', 'auditor')
PERMISSIONS = {
    'normal': ['products.own', 'catalog.read', 'profile.self', 'cart.self', 'orders.self', 'payment.self'],
    'merchant': ['catalog.read', 'profile.self', 'products.own', 'cart.self', 'orders.self', 'payment.self'],
    'admin': ['catalog.read', 'profile.self', 'cart.self', 'orders.self', 'payment.self', 'users.manage', 'products.manage', 'categories.manage', 'orders.manage', 'audit.read', 'audit.export', 'security.read'],
    'auditor': ['catalog.read', 'profile.self', 'audit.read', 'audit.export', 'security.read'],
}


def cipher():
    key = os.environ.get('MFA_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('请配置 MFA_ENCRYPTION_KEY，运行 python scripts/setup_security.py')
    return Fernet(key.encode())


def jwt():
    key = os.environ.get('JWT_SECRET_KEY')
    if not key or len(key) < 32:
        raise RuntimeError('JWT_SECRET_KEY 至少需要32个字符')
    return JWTUtils(key)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def totp(secret, step):
    key = base64.b32decode(secret, casefold=True)
    mac = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = mac[-1] & 15
    return f'{(struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7fffffff) % 1000000:06d}'


def state_for(db, user_id):
    state = db.query(SecurityState).filter_by(user_id=user_id).with_for_update().first()
    if state is None:
        state = SecurityState(user_id=user_id, enabled=False, last_step=-1,
                              recovery_hashes='[]', failures=0, locked_until=0, version=0)
        db.add(state)
        db.flush()
    return state


def audit(db, request, action, resource=None, result='success', user=None):
    info = user or getattr(request, 'user_info', {}) or {}
    db.add(AuditEvent(user_id=info.get('user_id'), username=info.get('username'),
                      role=info.get('role'), action=action,
                      resource=(resource or request.path)[:255], result=result,
                      ip=request.META.get('REMOTE_ADDR', '')[:64]))


def login_data(user, state, mfa=False):
    info = {'user_id': user.user_id, 'username': user.username, 'role': user.user_role.lower(),
            'mfa': mfa, 'security_version': state.version}
    return {'token': jwt().generate_token(info, expires_in_hours=2),
            'user': {**info, 'permissions': PERMISSIONS.get(info['role'], [])}}


def begin_login(db, user, request):
    from src.Data_base.models.user import User
    user = db.query(User).filter_by(user_id=user.user_id).populate_existing().with_for_update().one()
    state = state_for(db, user.user_id)
    info = {'user_id': user.user_id, 'username': user.username, 'role': user.user_role.lower()}
    if not user.is_active:
        raise ValueError('账号已停用')
    if info['role'] not in ('admin', 'auditor'):
        audit(db, request, 'auth.login', user=info)
        return login_data(user, state)
    now = int(time.time())
    if state.locked_until > now:
        raise ValueError('验证失败次数过多，请15分钟后重试')
    challenge = secrets.token_urlsafe(32)
    secret = None if state.enabled else base64.b32encode(secrets.token_bytes(20)).decode()
    db.query(LoginChallenge).filter(LoginChallenge.expires_at < now).delete(synchronize_session=False)
    # One live challenge per account. The row lock serializes concurrent logins.
    db.query(LoginChallenge).filter_by(user_id=user.user_id).delete(synchronize_session=False)
    db.add(LoginChallenge(challenge_hash=digest(challenge), user_id=user.user_id,
                         expires_at=now + 300, version=state.version,
                         pending_secret=cipher().encrypt(secret.encode()).decode() if secret else None))
    audit(db, request, 'auth.mfa.challenge', user=info)
    data = {'mfa_required': True, 'enrollment_required': not state.enabled,
            'challenge': challenge, 'expires_in': 300}
    if secret:
        data.update(secret=secret, provisioning_uri=f'otpauth://totp/{quote("SecureShop:" + user.username)}?secret={secret}&issuer=SecureShop&algorithm=SHA1&digits=6&period=30')
    return data


def verify_factor(state, code, encrypted_secret=None, now=None):
    now = int(time.time()) if now is None else now
    if state.locked_until > now:
        return False
    accepted = False
    if isinstance(code, str) and len(code) == 6 and code.isascii() and code.isdigit():
        secret = cipher().decrypt((encrypted_secret or state.secret).encode()).decode()
        for step in (now // 30 - 1, now // 30, now // 30 + 1):
            if step > state.last_step and hmac.compare_digest(totp(secret, step), code):
                state.last_step = step
                accepted = True
                break
    elif not encrypted_secret and state.enabled and isinstance(code, str):
        hashes = json.loads(state.recovery_hashes)
        candidate = digest(code.strip())
        for value in hashes:
            if hmac.compare_digest(value, candidate):
                hashes.remove(value)
                state.recovery_hashes = json.dumps(hashes)
                accepted = True
                break
    if accepted:
        state.failures = 0
        state.locked_until = 0
    else:
        state.failures += 1
        if state.failures >= 5:
            state.locked_until = now + 900
            state.failures = 0
    return accepted
