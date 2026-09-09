from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import time
from collections import defaultdict
import re
import json
from src.unified_service import UnifiedEcommerceService
from api_service.utils.jwt_balcklist import jwt_blacklist

class JWTAuthenticationMiddleware(MiddlewareMixin):
    PUBLIC = {'/api/auth/login', '/api/auth/cert/challenge', '/api/auth/cert/login',
              '/api/auth/cert/mtls-login', '/api/auth/mfa/verify',
              '/api/users/register', '/api/users/send-reset-code', '/api/users/reset-password',
              '/api/pay/callback', '/api/pay/sync-result', '/api/health'}

    def process_request(self, request):
        from src.Data_base.database import SessionLocal
        from src.Data_base.models.user import User
        from .security_core import jwt, state_for, audit
        path = request.path.rstrip('/')
        if not path.startswith('/api/') or request.method == 'OPTIONS':
            return None
        if path == '/api/auth/cert/file-login':
            return JsonResponse({'code': 403, 'message': '证书文件不能证明私钥持有，请使用密码或浏览器双向证书登录', 'data': None}, status=403)
        if path in self.PUBLIC or path.startswith('/api/docs') or path.startswith('/api/swagger'):
            return None
        if request.method == 'GET' and (path in ('/api/products', '/api/categories') or re.fullmatch(r'/api/products/\d+', path)):
            return None
        token = request.META.get('HTTP_AUTHORIZATION', '')
        payload = None
        if token.startswith('Bearer ') and not jwt_blacklist.is_blacklisted(token[7:]):
            try:
                payload = jwt().verify_token(token[7:])
            except (ValueError, TypeError, KeyError):
                pass
        with SessionLocal.begin() as db:
            user = db.get(User, payload.get('user_id')) if payload else None
            if not user or not user.is_active:
                audit(db, request, 'auth.denied', result='denied')
                return JsonResponse({'code': 401, 'message': '请重新登录', 'data': None}, status=401)
            state = state_for(db, user.user_id)
            role = user.user_role.lower()
            request.user_info = {'user_id': user.user_id, 'username': user.username, 'role': role}
            if payload.get('security_version', 0) != state.version or (role in ('admin', 'auditor') and (not payload.get('mfa') or not state.enabled)):
                audit(db, request, 'auth.session.revoked', result='denied')
                return JsonResponse({'code': 401, 'message': '会话已失效或尚未完成双因素验证，请重新登录', 'data': None}, status=401)
            allowed = role in ('normal', 'merchant', 'admin', 'auditor')
            if path.startswith('/api/admin/'):
                allowed = role == 'admin'
            elif path.startswith('/api/audit/'):
                allowed = role in ('admin', 'auditor') and request.method == 'GET'
            elif path.startswith('/api/merchant/'):
                allowed = role in ('admin', 'normal', 'merchant')
            elif path.startswith('/api/products') and request.method != 'GET':
                allowed = role in ('admin', 'normal', 'merchant')
            elif path.startswith('/api/categories') and request.method != 'GET':
                allowed = role == 'admin'
            elif path.startswith('/api/cache/'):
                allowed = role == 'admin'
            elif role == 'auditor' and not (path == '/api/users/profile' and request.method == 'GET' or path in ('/api/auth/logout', '/api/auth/mfa/rebind', '/api/users/change-password')):
                allowed = False
            if not allowed:
                audit(db, request, 'rbac.denied', result='denied')
                return JsonResponse({'code': 403, 'message': '当前角色无权执行此操作', 'data': None}, status=403)
        return None

    def process_response(self, request, response):
        from src.Data_base.database import SessionLocal
        from src.Data_base.models.user import User
        from .security_core import begin_login, audit
        path = request.path.rstrip('/')
        login_paths = {'/api/auth/login', '/api/auth/cert/login', '/api/auth/cert/mtls-login'}
        if path in login_paths and hasattr(response, 'data'):
            data = response.data.get('data') or {}
            if response.status_code == 200 and data.get('token'):
                with SessionLocal.begin() as db:
                    user = db.get(User, data.get('user', {}).get('user_id'))
                    try:
                        response.data['data'] = begin_login(db, user, request)
                        response.data['message'] = '请完成双因素验证' if response.data['data'].get('mfa_required') else '登录成功'
                    except ValueError as exc:
                        response.status_code = 403
                        response.data = {'code': 403, 'message': str(exc), 'data': None}
                response.content = response.rendered_content
            elif response.status_code >= 400:
                with SessionLocal.begin() as db:
                    audit(db, request, 'auth.login.failed', result='denied')
        if path.startswith('/api/') and getattr(request, 'user_info', None):
            if path in ('/api/auth/logout', '/api/users/change-password') and response.status_code == 200:
                from .security_core import state_for
                with SessionLocal.begin() as db:
                    state_for(db, request.user_info['user_id']).version += 1
            if request.method != 'GET' or response.status_code == 403:
                with SessionLocal.begin() as db:
                    audit(db, request, request.method.lower() + ' ' + path,
                          result='success' if response.status_code < 400 else 'denied')
        if path.startswith('/api/') and response.status_code >= 500:
            return JsonResponse({'code': 500, 'message': '服务暂时不可用，请稍后重试', 'data': None}, status=response.status_code)
        return response


class SecurityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        skip_paths = [
            '/api/auth/login',
            '/api/auth/mfa/',
            '/api/auth/cert/challenge',
            '/api/auth/cert/login',
            '/api/auth/cert/file-login',
            '/api/auth/cert/mtls-login',
        ]
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        # SQL注入检测
        if request.method in ['POST', 'PUT', 'GET']:
            for key, value in request.GET.items():
                if self.detect_sql_injection(str(value)):
                    return JsonResponse({
                        "code": 400,
                        "message": "输入包含非法字符",
                        "data": None,
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
                    }, status=400)

            if request.method in ['POST', 'PUT'] and request.content_type == 'application/json':
                try:
                    body = json.loads(request.body)
                    if self.check_json_for_injection(body):
                        return JsonResponse({
                            "code": 400,
                            "message": "输入包含非法字符",
                            "data": None,
                            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
                        }, status=400)
                except json.JSONDecodeError:
                    pass

        return None

    def detect_sql_injection(self, input_string):
        # 放宽SQL注入检测规则，避免误判中文关键词
        sql_patterns = [
            # 单个SQL关键字
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|UNION)\b",
            # SQL注释符
            r"(--|\#|/\*|\*/)",
            # 分号结束符
            r";\s*$",
            # 单引号闭合攻击
            r"'\s*(OR|AND)\s+['\d]",
            # 恒真条件
            r"\b(OR|AND)\s+['\"]?['\"]?=*['\"]?['\"]?",
        ]
        combined_pattern = "|".join(sql_patterns)
        return bool(re.search(combined_pattern, input_string, re.IGNORECASE))

    def check_json_for_injection(self, data):
        if isinstance(data, dict):
            for value in data.values():
                if self.check_json_for_injection(value):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self.check_json_for_injection(item):
                    return True
        elif isinstance(data, str):
            return self.detect_sql_injection(data)
        return False

    def process_response(self, request, response):
        # 安全头部
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        return response


class RateLimitMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.requests = defaultdict(list)

    def process_request(self, request):
        # 排除公开API的限流
        excluded_paths = [
            '/api/docs/',
            '/api/swagger/',
            '/api/pay/callback',
            '/api/pay/sync-result',
            '/api/products',  # 商品列表公开，不限流
        ]

        if any(request.path.startswith(path) for path in excluded_paths):
            return None

        client_ip = self.get_client_ip(request)
        current_time = time.time()

        # 清理过期请求（60秒窗口）
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]

        # 检查限制（最大100个请求）
        if len(self.requests[client_ip]) >= 100:
            return JsonResponse({
                "code": 429,
                "message": "请求频率过高",
                "data": None,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
            }, status=429)

        self.requests[client_ip].append(current_time)
        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
