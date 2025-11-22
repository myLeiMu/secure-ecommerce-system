from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import time
from collections import defaultdict
import re
import json
from src.unified_service import UnifiedEcommerceService
from api_service.utils.jwt_balcklist import jwt_blacklist

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print(f"[JWT DEBUG] 请求路径: {request.path}")

        # 不需要认证的路径
        excluded_paths = [
            '/api/auth/login',
            '/api/users/register',
            '/api/users/send-reset-code',
            '/api/users/reset-password',
            '/api/docs/',
            '/api/swagger/',
            '/admin/',
            '/api/products',
            '/api/categories',
            '/api/products',
            '/api/health',
            '/api/v1/api/login',
            '/api/v1/api/register',
        ]

        if any(request.path.startswith(path) for path in excluded_paths):
            print(f"[JWT DEBUG] 路径 {request.path} 被排除，跳过认证")
            request.user = None
            return None

        # 从Header获取token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"[JWT DEBUG] Authorization Header: {auth_header}")

        if not auth_header.startswith('Bearer '):
            print("[JWT DEBUG] 未提供Bearer token")
            return JsonResponse({
                "code": 401,
                "message": "未提供认证令牌",
                "data": None,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
            }, status=401)

        token = auth_header[7:]
        print(f"[JWT DEBUG] 提取的token: {token[:20]}...")

        # 检查令牌是否在黑名单中
        if jwt_blacklist.is_blacklisted(token):
            print("[JWT DEBUG] 令牌已在黑名单中")
            return JsonResponse({
                "code": 401,
                "message": "令牌已失效",
                "data": None,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
            }, status=401)

        try:
            service = UnifiedEcommerceService()
            payload = service.verify_token(token)
            print(f"[JWT DEBUG] Token验证结果: {payload}")

            if payload:
                # 创建一个简单的用户对象，避免 AnonymousUser 问题
                from django.contrib.auth.models import AnonymousUser
                request.user = AnonymousUser()
                # 同时将用户信息存储在自定义属性中
                request.user_info = {
                    'user_id': payload.get('user_id'),
                    'username': payload.get('username'),
                    'role': payload.get('role', 'normal')
                }
                print(f"[JWT DEBUG] 用户认证成功: {request.user_info}")
                return None  # 认证成功，继续处理
            else:
                print("[JWT DEBUG] Token无效或验证失败")
                return JsonResponse({
                    "code": 401,
                    "message": "令牌无效或已过期",
                    "data": None,
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
                }, status=401)

        except Exception as e:
            print(f"[JWT DEBUG] 认证异常: {str(e)}")
            import traceback
            print(f"[JWT DEBUG] 异常详情: {traceback.format_exc()}")
            return JsonResponse({
                "code": 401,
                "message": f"认证失败: {str(e)}",
                "data": None,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
            }, status=401)


class SecurityMiddleware(MiddlewareMixin):
    def process_request(self, request):
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