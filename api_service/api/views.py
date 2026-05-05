from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import exception_handler
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timezone
from decimal import Decimal
import time
import secrets
import requests
from typing import Optional
from urllib.parse import urlencode, unquote
import sys
import os
from django.http import JsonResponse
from api_service.utils.jwt_balcklist import jwt_blacklist
from api_service.utils.cache_utils import ProductCache, UserCache
from api_service.utils.redis_client import redis_client
from api_service.api.payment_crypto import open_result_envelope, sign_payment_params
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.unified_service import UnifiedEcommerceService
from sqlalchemy.orm import joinedload
from gmssl import sm2
from src.algorithm.ca_center import parse_certificate_pem, verify_certificate_with_root
from src.Data_base.models.product import Product
from src.Data_base.models.user import User
from src.Data_base.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    CartItem,
    Payment,
    PaymentStatus,
    PaymentMethod,
)


# 统一响应格式
class APIResponse:
    @staticmethod
    def success(data=None, message="success", code=0):
        return {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def error(message="error", code=400, data=None):
        return {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        if status_code == 401:
            return Response({
                "code": 401,
                "message": "未认证",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)
        elif status_code == 403:
            return Response({
                "code": 403,
                "message": "权限不足",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=403)
        elif status_code == 404:
            return Response({
                "code": 404,
                "message": "资源不存在",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=404)
        elif status_code == 400:
            if hasattr(exc, 'detail'):
                message = str(exc.detail)
            else:
                message = "请求参数错误"
            return Response({
                "code": 400,
                "message": message,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

    return Response({
        "code": 500,
        "message": "服务器内部错误",
        "data": None,
        "timestamp": datetime.now().isoformat()
    }, status=500)


# 序列化器
from rest_framework import serializers


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True, help_text="用户名")
    password = serializers.CharField(max_length=128, required=True, help_text="密码", write_only=True)
    phone = serializers.CharField(max_length=20, required=True, help_text="手机号")
    code = serializers.CharField(max_length=6, required=True, help_text="验证码")
    email = serializers.EmailField(required=False, help_text="邮箱")


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True, help_text="用户名")
    password = serializers.CharField(max_length=128, required=True, help_text="密码", write_only=True)


class CertChallengeSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True, help_text="用户名")


class CertLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True, help_text="用户名")
    certificate_pem = serializers.CharField(required=True, help_text="PEM证书")
    challenge = serializers.CharField(required=True, help_text="挑战字符串")
    signature_hex = serializers.CharField(required=True, help_text="SM2签名hex")


class CertFileLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True, help_text="用户名")
    certificate_pem = serializers.CharField(required=True, help_text="PEM证书")


class CertMTLSLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=False, help_text="用户名（可选）")


class UserProfileSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True, help_text="用户ID")
    username = serializers.CharField(read_only=True, help_text="用户名")
    email = serializers.EmailField(read_only=True, help_text="邮箱")
    phone = serializers.CharField(read_only=True, help_text="手机号")
    bank_card_number = serializers.CharField(read_only=True, help_text="银行卡号")
    user_role = serializers.CharField(read_only=True, help_text="用户角色")
    is_verified = serializers.BooleanField(read_only=True, help_text="是否验证")
    last_login = serializers.DateTimeField(read_only=True, help_text="最后登录时间")
    created_at = serializers.DateTimeField(read_only=True, help_text="创建时间")


class BankCardBindSerializer(serializers.Serializer):
    bank_card_number = serializers.CharField(max_length=64, required=True, help_text="银行卡号")


class ProductListQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(required=False, help_text="搜索关键词")
    category_id = serializers.IntegerField(required=False, help_text="分类ID")
    min_price = serializers.FloatField(required=False, help_text="最低价格")
    max_price = serializers.FloatField(required=False, help_text="最高价格")


class ProductCreateSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50, required=True, help_text="SKU")
    product_name = serializers.CharField(max_length=200, required=True, help_text="商品名")
    description = serializers.CharField(required=False, allow_blank=True, help_text="商品描述")
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, help_text="售价")
    stock_quantity = serializers.IntegerField(required=True, min_value=0, help_text="库存")
    category_id = serializers.IntegerField(required=True, help_text="分类ID")
    image_urls = serializers.ListField(required=False, child=serializers.CharField(), help_text="图片URL列表")
    specifications = serializers.JSONField(required=False, help_text="规格")


class ProductUpdateSerializer(serializers.Serializer):
    product_name = serializers.CharField(max_length=200, required=False, help_text="商品名")
    description = serializers.CharField(required=False, allow_blank=True, help_text="商品描述")
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, help_text="售价")
    stock_quantity = serializers.IntegerField(required=False, min_value=0, help_text="库存")
    category_id = serializers.IntegerField(required=False, help_text="分类ID")
    image_urls = serializers.ListField(required=False, child=serializers.CharField(), help_text="图片URL列表")
    specifications = serializers.JSONField(required=False, help_text="规格")
    is_available = serializers.BooleanField(required=False, help_text="是否上架")


class CartUpsertSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True, help_text="商品ID")
    quantity = serializers.IntegerField(required=True, min_value=1, help_text="数量")


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(required=True, min_value=1, help_text="数量")


class OrderCreateFromCartSerializer(serializers.Serializer):
    shipping_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal("0.00"))
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal("0.00"))


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, required=True, help_text="原密码", write_only=True)
    new_password = serializers.CharField(max_length=128, required=True, help_text="新密码", write_only=True)


class PasswordResetCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=True, help_text="手机号")


class PasswordResetSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=True, help_text="手机号")
    code = serializers.CharField(max_length=6, required=True, help_text="验证码")
    new_password = serializers.CharField(max_length=128, required=True, help_text="新密码", write_only=True)


CERT_LOGIN_CHALLENGES = {}
CERT_LOGIN_CHALLENGE_TTL_SECONDS = 300


def _resolve_root_cert_path() -> str:
    env_path = os.getenv("CA_ROOT_CERT_PATH")
    candidate_paths = []
    if env_path:
        candidate_paths.append(env_path)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths.extend([
        os.path.join(project_root, "keys", "ca", "root_ca.crt.pem"),
        os.path.join(os.getcwd(), "keys", "ca", "root_ca.crt.pem"),
        os.path.join(os.path.dirname(os.getcwd()), "keys", "ca", "root_ca.crt.pem"),
    ])

    for path in candidate_paths:
        absolute = path if os.path.isabs(path) else os.path.abspath(path)
        if os.path.exists(absolute):
            return absolute
    return ""


def _extract_cn_from_dn(dn: str) -> str:
    if not dn:
        return ""
    parts = [p.strip() for p in dn.split(",")]
    for p in parts:
        if p.startswith("CN="):
            return p[3:].strip()
        if p.startswith("/CN="):
            return p[4:].strip()
    return ""


def _verify_certificate_chain_no_crl(certificate_pem: str, expected_username: Optional[str] = None):
    root_cert_path = _resolve_root_cert_path()
    if not root_cert_path:
        return False, "根证书不存在", None
    with open(root_cert_path, "r", encoding="utf-8") as f:
        root_cert_pem = f.read()
    cert_ok = verify_certificate_with_root(certificate_pem, root_cert_pem)
    if not cert_ok:
        return False, "证书无效", None
    try:
        cert_info = parse_certificate_pem(certificate_pem)
    except Exception:
        return False, "证书无效", None
    now = datetime.now(timezone.utc)
    if cert_info.get("not_after") and now > cert_info["not_after"]:
        return False, "证书已过期", None
    if cert_info.get("not_before") and now < cert_info["not_before"]:
        return False, "证书尚未生效", None
    cert_cn = cert_info.get("subject_common_name", "")
    if expected_username and cert_cn and cert_cn != expected_username:
        return False, "证书与用户名不匹配", None
    return True, "", cert_info


def _get_user_info(request):
    user_info = getattr(request, 'user_info', None)
    if not user_info:
        return None
    if not user_info.get("user_id"):
        return None
    return user_info


def _serialize_product(product: Product):
    return {
        'product_id': product.product_id,
        'sku': product.sku,
        'product_name': product.product_name,
        'description': product.description or '',
        'sale_price': float(product.sale_price),
        'stock_quantity': product.stock_quantity,
        'image_urls': product.image_urls or [],
        'category_id': product.category_id,
        'seller_id': getattr(product, 'seller_id', None),
        'is_available': bool(product.is_available),
        'created_at': product.created_at,
        'updated_at': product.updated_at,
    }


@method_decorator(csrf_exempt, name='dispatch')
class CertChallengeView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="证书登录挑战",
        operation_description="生成证书登录挑战字符串",
        request_body=CertChallengeSerializer,
        tags=['用户认证']
    )
    def post(self, request):
        serializer = CertChallengeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)
        username = serializer.validated_data["username"]
        challenge = secrets.token_urlsafe(32)
        CERT_LOGIN_CHALLENGES[username] = {
            "challenge": challenge,
            "expires_at": time.time() + CERT_LOGIN_CHALLENGE_TTL_SECONDS
        }
        return Response({
            "code": 0,
            "message": "success",
            "data": {
                "challenge": challenge,
                "expires_in": CERT_LOGIN_CHALLENGE_TTL_SECONDS
            },
            "timestamp": datetime.now().isoformat()
        })


@method_decorator(csrf_exempt, name='dispatch')
class CertLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="证书登录",
        operation_description="使用SM2证书与签名进行登录，成功后返回JWT",
        request_body=CertLoginSerializer,
        tags=['用户认证']
    )
    def post(self, request):
        serializer = CertLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        username = serializer.validated_data["username"]
        certificate_pem = serializer.validated_data["certificate_pem"]
        challenge = serializer.validated_data["challenge"]
        signature_hex = serializer.validated_data["signature_hex"]

        challenge_state = CERT_LOGIN_CHALLENGES.get(username)
        if not challenge_state:
            return Response({
                "code": 401,
                "message": "挑战不存在，请先获取挑战",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        if time.time() > challenge_state["expires_at"]:
            CERT_LOGIN_CHALLENGES.pop(username, None)
            return Response({
                "code": 401,
                "message": "挑战已过期，请重新获取",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        if challenge != challenge_state["challenge"]:
            return Response({
                "code": 401,
                "message": "挑战不匹配",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        try:
            verify_ok, verify_message, cert_info = _verify_certificate_chain_no_crl(
                certificate_pem=certificate_pem,
                expected_username=username
            )
            if not verify_ok:
                status = 500 if verify_message == "根证书不存在" else 401
                return Response({
                    "code": status,
                    "message": verify_message,
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=status)

            verifier = sm2.CryptSM2(public_key=cert_info["subject_public_key_hex"], private_key="")
            if not verifier.verify(signature_hex, challenge.encode("utf-8")):
                return Response({
                    "code": 401,
                    "message": "签名校验失败",
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=401)

            service = UnifiedEcommerceService()
            result = service.cert_login_user(username)
            if not result.get("success"):
                return Response({
                    "code": 401,
                    "message": result.get("message", "证书登录失败"),
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=401)
            CERT_LOGIN_CHALLENGES.pop(username, None)
            return Response({
                "code": 0,
                "message": result.get("message", "登录成功"),
                "data": {
                    "token": result.get("token"),
                    "user": result.get("user")
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                "code": 500,
                "message": f"证书登录异常: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CertFileLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="证书文件登录",
        operation_description="前端上传PEM证书字符串，后端验签后返回JWT",
        request_body=CertFileLoginSerializer,
        tags=['用户认证']
    )
    def post(self, request):
        serializer = CertFileLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        username = serializer.validated_data["username"]
        certificate_pem = serializer.validated_data["certificate_pem"]

        try:
            verify_ok, verify_message, _ = _verify_certificate_chain_no_crl(
                certificate_pem=certificate_pem,
                expected_username=username
            )
            if not verify_ok:
                status = 500 if verify_message == "根证书不存在" else 401
                return Response({
                    "code": status,
                    "message": verify_message,
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=status)

            service = UnifiedEcommerceService()
            result = service.cert_login_user(username)
            if not result.get("success"):
                return Response({
                    "code": 401,
                    "message": result.get("message", "证书登录失败"),
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=401)

            return Response({
                "code": 0,
                "message": result.get("message", "登录成功"),
                "data": {
                    "token": result.get("token"),
                    "user": result.get("user")
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                "code": 500,
                "message": f"证书文件登录异常: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CertMTLSLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="mTLS证书登录",
        operation_description="通过反向代理透传的客户端证书进行登录，成功后返回JWT",
        request_body=CertMTLSLoginSerializer,
        tags=['用户认证']
    )
    def post(self, request):
        serializer = CertMTLSLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        verify_header = request.META.get("HTTP_X_SSL_CLIENT_VERIFY", "")
        if verify_header and verify_header.upper() != "SUCCESS":
            return Response({
                "code": 401,
                "message": "客户端证书握手未通过",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        cert_header = request.META.get("HTTP_X_SSL_CLIENT_CERT") or request.META.get("HTTP_X_CLIENT_CERT_PEM")
        if not cert_header:
            return Response({
                "code": 401,
                "message": "未提供客户端证书",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        certificate_pem = unquote(cert_header)
        strict_backend_verify = os.getenv("MTLS_BACKEND_VERIFY", "false").lower() in {"1", "true", "yes"}

        try:
            cert_cn = ""
            if strict_backend_verify:
                verify_ok, verify_message, cert_info = _verify_certificate_chain_no_crl(certificate_pem=certificate_pem)
                if not verify_ok:
                    status = 500 if verify_message == "根证书不存在" else 401
                    return Response({
                        "code": status,
                        "message": verify_message,
                        "data": None,
                        "timestamp": datetime.now().isoformat()
                    }, status=status)
                cert_cn = cert_info.get("subject_common_name", "")
            else:
                try:
                    cert_info = parse_certificate_pem(certificate_pem)
                    cert_cn = cert_info.get("subject_common_name", "")
                except Exception:
                    cert_cn = _extract_cn_from_dn(request.META.get("HTTP_X_SSL_CLIENT_S_DN", ""))

            input_username = serializer.validated_data.get("username")
            login_username = input_username or cert_cn

            if input_username and cert_cn and input_username != cert_cn:
                return Response({
                    "code": 401,
                    "message": "证书主体与用户名不一致",
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=401)

            if not login_username:
                return Response({
                    "code": 400,
                    "message": "无法从证书中解析用户名",
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=400)

            service = UnifiedEcommerceService()
            result = service.cert_login_user(login_username)
            if not result.get("success"):
                return Response({
                    "code": 401,
                    "message": result.get("message", "证书登录失败"),
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=401)

            return Response({
                "code": 0,
                "message": result.get("message", "登录成功"),
                "data": {
                    "token": result.get("token"),
                    "user": result.get("user")
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                "code": 500,
                "message": f"mTLS证书登录异常: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


# API视图
@method_decorator(csrf_exempt, name='dispatch')
class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="用户注册",
        operation_description="使用用户名、密码、手机号和验证码进行用户注册",
        request_body=UserRegistrationSerializer,
        responses={
            200: openapi.Response(
                description="注册成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='数据', nullable=True),
                        'timestamp': openapi.Schema(type=openapi.TYPE_STRING, description='时间戳'),
                    }
                ),
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "注册成功",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            400: openapi.Response(
                description="注册失败",
                examples={
                    "application/json": {
                        "code": 400,
                        "message": "用户名已存在",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            500: openapi.Response(
                description="服务器错误",
                examples={
                    "application/json": {
                        "code": 500,
                        "message": "服务器内部错误",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户认证']
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        try:
            service = UnifiedEcommerceService()
            result = service.register_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                phone=serializer.validated_data['phone'],
                code=serializer.validated_data['code'],
                email=serializer.validated_data.get('email')
            )

            if result['success']:
                return Response({
                    "code": 0,
                    "message": result['message'],
                    "data": result.get("data"),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return Response({
                    "code": 400,
                    "message": result['message'],
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=400)

        except Exception as e:
            return Response({
                "code": 500,
                "message": f"注册失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class UserLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="用户登录",
        operation_description="使用用户名和密码进行登录",
        request_body=UserLoginSerializer,
        responses={
            200: openapi.Response(
                description="登录成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'token': openapi.Schema(type=openapi.TYPE_STRING),
                                'user': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                                    }
                                )
                            }
                        ),
                        'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                ),
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "登录成功",
                        "data": {
                            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "user_id": 1,
                                "username": "testuser"
                            }
                        },
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            401: openapi.Response(
                description="登录失败",
                examples={
                    "application/json": {
                        "code": 401,
                        "message": "用户名或密码错误",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户认证']
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        try:
            service = UnifiedEcommerceService()
            result = service.login_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )

            if result['success']:
                return Response({
                    "code": 0,
                    "message": result['message'],
                    "data": {
                        'token': result.get('token'),
                        'user': result.get('user')
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return Response({
                    "code": 401,
                    "message": result['message'],
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=401)

        except Exception as e:
            return Response({
                "code": 500,
                "message": f"登录失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


class PasswordChangeView(APIView):

    @swagger_auto_schema(
        operation_summary="修改密码",
        operation_description="已登录用户修改密码",
        request_body=PasswordChangeSerializer,
        responses={
            200: openapi.Response(
                description="修改成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "密码修改成功",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            400: openapi.Response(
                description="修改失败",
                examples={
                    "application/json": {
                        "code": 400,
                        "message": "原密码错误",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            401: openapi.Response(
                description="未认证",
                examples={
                    "application/json": {
                        "code": 401,
                        "message": "用户未认证",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户管理'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        if not hasattr(request, 'user_info') or not request.user_info:
            return Response({
                "code": 401,
                "message": "用户未认证",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        username = request.user_info.get('username')
        service = UnifiedEcommerceService()
        result = service.change_password(
            username=username,
            old_password=serializer.validated_data['old_password'],
            new_password=serializer.validated_data['new_password']
        )

        status_code = 200 if result['success'] else 400
        return Response({
            "code": 0 if result['success'] else 400,
            "message": result['message'],
            "data": None,
            "timestamp": datetime.now().isoformat()
        }, status=status_code)


class PasswordResetCodeView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="发送重置密码验证码",
        operation_description="向指定手机号发送重置密码的验证码",
        request_body=PasswordResetCodeSerializer,
        responses={
            200: openapi.Response(
                description="发送成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "验证码发送成功",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            400: openapi.Response(
                description="发送失败",
                examples={
                    "application/json": {
                        "code": 400,
                        "message": "手机号未注册",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户管理']
    )
    def post(self, request):
        serializer = PasswordResetCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        service = UnifiedEcommerceService()
        result = service.send_reset_code(serializer.validated_data['phone'])
        status_code = 200 if result['success'] else 400
        return Response({
            "code": 0 if result['success'] else 400,
            "message": result['message'],
            "data": None,
            "timestamp": datetime.now().isoformat()
        }, status=status_code)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="重置密码",
        operation_description="使用手机号和验证码重置密码",
        request_body=PasswordResetSerializer,
        responses={
            200: openapi.Response(
                description="重置成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "密码重置成功",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            400: openapi.Response(
                description="重置失败",
                examples={
                    "application/json": {
                        "code": 400,
                        "message": "验证码错误或已过期",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户管理']
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": 400,
                "message": serializer.errors,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        service = UnifiedEcommerceService()
        result = service.reset_password(
            phone=serializer.validated_data['phone'],
            new_password=serializer.validated_data['new_password'],
            code=serializer.validated_data['code']
        )
        status_code = 200 if result['success'] else 400
        return Response({
            "code": 0 if result['success'] else 400,
            "message": result['message'],
            "data": None,
            "timestamp": datetime.now().isoformat()
        }, status=status_code)


@method_decorator(csrf_exempt, name='dispatch')
class UserLogoutView(APIView):

    @swagger_auto_schema(
        operation_summary="用户登出",
        operation_description="用户登出，将令牌加入黑名单",
        responses={
            200: openapi.Response(
                description="登出成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "登出成功",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户认证'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                # 将令牌加入Redis黑名单
                jwt_blacklist.add_token(token)

                # 调用原有的登出逻辑
                service = UnifiedEcommerceService()
                result = service.user_system.logout(token)
                print(f"[LOGOUT] 用户登出，令牌已加入Redis黑名单")
            except Exception as e:
                print(f"[LOGOUT ERROR] 登出异常: {e}")

        return Response({
            "code": 0,
            "message": "登出成功",
            "data": None,
            "timestamp": datetime.now().isoformat()
        }, status=200)


class UserProfileView(APIView):

    @swagger_auto_schema(
        operation_summary="获取用户信息",
        operation_description="获取当前用户的详细信息",
        responses={
            200: openapi.Response(
                description="获取成功",
                schema=UserProfileSerializer,
            ),
            401: openapi.Response(
                description="未认证",
                examples={
                    "application/json": {
                        "code": 401,
                        "message": "用户未认证",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            404: openapi.Response(
                description="用户不存在",
                examples={
                    "application/json": {
                        "code": 404,
                        "message": "用户信息获取失败",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户管理'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        print(f"[Profile DEBUG] request.user_info: {getattr(request, 'user_info', 'NOT SET')}")

        # 检查用户认证状态
        if not hasattr(request, 'user_info') or not request.user_info:
            print("[Profile DEBUG] 用户未认证")
            return JsonResponse({
                "code": 401,
                "message": "用户未认证",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        try:
            # 使用缓存获取用户信息
            username = request.user_info['username']
            user_info = UserCache.get_user_profile(username)

            print(f"[Profile DEBUG] 获取的用户信息: {user_info}")

            if user_info:
                # 直接构建响应数据
                if isinstance(user_info, dict):
                    user_data = user_info
                else:
                    # 如果是对象，手动转换为字典
                    user_data = {}
                    for field in ['user_id', 'username', 'email', 'phone', 'bank_card_number', 'user_role',
                                  'is_verified', 'last_login', 'created_at']:
                        if hasattr(user_info, field):
                            value = getattr(user_info, field)
                            # 处理日期时间对象
                            if field in ['last_login', 'created_at'] and value:
                                user_data[field] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                            else:
                                user_data[field] = value

                return JsonResponse({
                    "code": 0,
                    "message": "success",
                    "data": user_data,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return JsonResponse({
                    "code": 404,
                    "message": "用户信息获取失败",
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=404)

        except Exception as e:
            import traceback
            print(f"[Profile DEBUG] 获取用户信息错误: {str(e)}")
            print(f"[Profile DEBUG] 异常详情: {traceback.format_exc()}")

            return JsonResponse({
                "code": 500,
                "message": f"获取用户信息失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)

    @swagger_auto_schema(
        operation_summary="更新用户信息",
        operation_description="更新当前用户的个人信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='用户名'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='邮箱'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='手机号'),
            }
        ),
        responses={
            200: openapi.Response(
                description="更新成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "用户信息更新成功",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            400: openapi.Response(
                description="更新失败",
                examples={
                    "application/json": {
                        "code": 400,
                        "message": "用户名已存在",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            401: openapi.Response(
                description="未认证",
                examples={
                    "application/json": {
                        "code": 401,
                        "message": "用户未认证",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['用户管理'],
        security=[{'Bearer': []}]
    )
    def put(self, request):
        """更新用户资料"""
        if not hasattr(request, 'user_info') or not request.user_info:
            return Response({
                "code": 401,
                "message": "用户未认证",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=401)

        try:
            username = request.user_info['username']
            update_data = request.data

            # 使用 UnifiedEcommerceService 更新用户资料
            service = UnifiedEcommerceService()
            result = service.update_user_profile(username, update_data)

            if result['success']:
                # 清理用户缓存，确保下次获取的是最新数据
                try:
                    from api_service.utils.cache_utils import UserCache
                    UserCache.invalidate_user_caches(username)
                    print(f"[缓存] 已清理用户 {username} 的缓存")
                except Exception as cache_error:
                    # 缓存清理失败不影响主要功能，只记录日志
                    print(f"[缓存警告] 清理用户缓存失败: {cache_error}")
                    # 继续执行，不抛出异常

                return Response({
                    "code": 0,
                    "message": result['message'],
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return Response({
                    "code": 400,
                    "message": result['message'],
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=400)

        except Exception as e:
            import traceback
            print(f"更新用户资料错误: {str(e)}")
            print(f"异常详情: {traceback.format_exc()}")

            return Response({
                "code": 500,
                "message": f"更新资料失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


class BankCardBindView(APIView):
    @swagger_auto_schema(
        operation_summary="绑定银行卡",
        request_body=BankCardBindSerializer,
        tags=['用户管理'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        serializer = BankCardBindSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse.error(serializer.errors, 400), status=400)

        card_no = serializer.validated_data["bank_card_number"].replace(" ", "")
        if not card_no.isdigit() or not (12 <= len(card_no) <= 32):
            return Response(APIResponse.error("银行卡号格式不正确", 400), status=400)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            user = db.query(User).filter(User.user_id == user_info["user_id"]).first()
            if not user:
                return Response(APIResponse.error("用户不存在", 404), status=404)
            user.bank_card_number = card_no
            db.commit()
            UserCache.invalidate_user_caches(user.username)
            return Response(APIResponse.success({
                "bank_card_number": card_no,
                "bank_card_last_four": card_no[-4:],
            }, "银行卡绑定成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"绑定银行卡失败: {str(e)}", 500), status=500)


# 商品相关视图
class ProductListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="获取商品列表",
        operation_description="根据关键词、分类、价格范围搜索商品",
        manual_parameters=[
            openapi.Parameter('keyword', openapi.IN_QUERY, description="搜索关键词", type=openapi.TYPE_STRING),
            openapi.Parameter('category_id', openapi.IN_QUERY, description="分类ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('min_price', openapi.IN_QUERY, description="最低价格", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="最高价格", type=openapi.TYPE_NUMBER),
        ],
        responses={
            200: openapi.Response(
                description="获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": [
                            {
                                "product_id": 1,
                                "product_name": "示例商品",
                                "sale_price": 99.99,
                                "stock_quantity": 100,
                                "image_urls": ["http://example.com/image1.jpg"]
                            }
                        ],
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            500: openapi.Response(
                description="服务器错误",
                examples={
                    "application/json": {
                        "code": 500,
                        "message": "获取商品列表失败",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['商品管理']
    )
    def get(self, request):
        try:
            keyword = request.GET.get('keyword')
            category_id = request.GET.get('category_id')
            min_price = request.GET.get('min_price')
            max_price = request.GET.get('max_price')

            # 参数验证和转换
            try:
                category_id = int(category_id) if category_id and category_id != 'null' else None
            except (ValueError, TypeError):
                category_id = None

            try:
                min_price = float(min_price) if min_price and min_price != 'null' else None
            except (ValueError, TypeError):
                min_price = None

            try:
                max_price = float(max_price) if max_price and max_price != 'null' else None
            except (ValueError, TypeError):
                max_price = None

            # 使用缓存获取商品列表
            products = ProductCache.get_product_list(
                keyword=keyword,
                category_id=category_id,
                min_price=min_price,
                max_price=max_price
            )

            # 将 Product 对象转换为可序列化的字典
            serialized_products = []
            if products:
                for product in products:
                    # 检查 product 是否是字典，如果不是则转换为字典
                    if isinstance(product, dict):
                        serialized_products.append({
                            'product_id': product.get('product_id'),
                            'sku': product.get('sku', ''),
                            'product_name': product.get('product_name', ''),
                            'description': product.get('description', ''),
                            'sale_price': float(product.get('sale_price', 0)),
                            'stock_quantity': product.get('stock_quantity', 0),
                            'image_urls': product.get('image_urls', []),
                            'category_id': product.get('category_id'),
                            'seller_id': product.get('seller_id'),
                            'is_available': bool(product.get('is_available', True)),
                            'created_at': product.get('created_at'),
                            'updated_at': product.get('updated_at'),
                        })
                    else:
                        serialized_products.append(_serialize_product(product))

            return Response({
                "code": 0,
                "message": "success",
                "data": serialized_products,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            import traceback
            print(f"获取商品列表错误: {str(e)}")
            print(traceback.format_exc())

            return Response({
                "code": 500,
                "message": f"获取商品列表失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)

    @swagger_auto_schema(
        operation_summary="发布商品",
        operation_description="卖家发布商品（需要JWT）",
        request_body=ProductCreateSerializer,
        tags=['商品管理'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse.error(serializer.errors, 400), status=400)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            data = serializer.validated_data
            exists = db.query(Product).filter(Product.sku == data["sku"]).first()
            if exists:
                return Response(APIResponse.error("SKU已存在", 400), status=400)

            product = Product(
                sku=data["sku"],
                product_name=data["product_name"],
                description=data.get("description", ""),
                sale_price=data["sale_price"],
                stock_quantity=data["stock_quantity"],
                category_id=data["category_id"],
                image_urls=data.get("image_urls", []),
                specifications=data.get("specifications", {}),
                seller_id=user_info["user_id"],
                status='active',
                is_active=True,
                is_available=True,
                track_inventory=True,
            )
            db.add(product)
            db.commit()
            db.refresh(product)
            ProductCache.invalidate_product_caches()
            return Response(APIResponse.success(_serialize_product(product), "发布成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"发布失败: {str(e)}", 500), status=500)


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="获取分类列表",
        operation_description="获取所有商品分类的树形结构",
        responses={
            200: openapi.Response(
                description="获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": [
                            {
                                "category_id": 1,
                                "category_name": "电子产品",
                                "parent_id": None,
                                "level": 1,
                                "sort_order": 0,
                                "children": [
                                    {
                                        "category_id": 2,
                                        "category_name": "手机",
                                        "parent_id": 1,
                                        "level": 2,
                                        "sort_order": 0
                                    }
                                ]
                            }
                        ],
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            500: openapi.Response(
                description="服务器错误",
                examples={
                    "application/json": {
                        "code": 500,
                        "message": "获取分类列表失败",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['商品管理']
    )
    def get(self, request):
        """获取分类列表"""
        try:
            print("开始处理分类列表请求")
            service = UnifiedEcommerceService()

            # 获取顶级分类
            top_categories = service.category_repo.get_categories_tree()
            print(f"获取到 {len(top_categories)} 个顶级分类")

            if not top_categories:
                print("没有找到任何分类数据")
                return Response({
                    "code": 0,
                    "message": "success",
                    "data": [],
                    "timestamp": datetime.now().isoformat()
                })

            # 构建分类树
            category_list = []
            for category in top_categories:
                print(f"处理分类: {category.category_name} (ID: {category.category_id})")

                # 获取子分类
                subcategories = service.category_repo.get_subcategories(category.category_id)
                print(f"  ├─ 子分类数量: {len(subcategories)}")

                category_dict = {
                    'category_id': getattr(category, 'category_id', None),
                    'category_name': getattr(category, 'category_name', ''),
                    'parent_id': getattr(category, 'parent_category_id', None),
                    'level': getattr(category, 'category_level', 1),
                    'sort_order': getattr(category, 'sort_order', 0),
                    'children': []
                }

                # 处理子分类
                for child in subcategories:
                    child_dict = {
                        'category_id': getattr(child, 'category_id', None),
                        'category_name': getattr(child, 'category_name', ''),
                        'parent_id': getattr(child, 'parent_category_id', None),
                        'level': getattr(child, 'category_level', 2),
                        'sort_order': getattr(child, 'sort_order', 0)
                    }
                    category_dict['children'].append(child_dict)
                    print(f"  ├─ 子分类: {child.category_name} (ID: {child.category_id})")

                category_list.append(category_dict)

            print(f"返回分类数据: {len(category_list)} 个分类组")
            return Response({
                "code": 0,
                "message": "success",
                "data": category_list,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            import traceback
            print(f"获取分类列表错误: {str(e)}")
            print(f"异常详情: {traceback.format_exc()}")

            return Response({
                "code": 500,
                "message": f"获取分类列表失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="获取商品详情",
        operation_description="根据商品ID获取商品详细信息",
        responses={
            200: openapi.Response(
                description="获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": {
                            "product_id": 1,
                            "product_name": "示例商品",
                            "description": "商品详细描述",
                            "sale_price": 99.99,
                            "stock_quantity": 100,
                            "image_urls": [
                                "http://example.com/image1.jpg",
                                "http://example.com/image2.jpg"
                            ]
                        },
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            404: openapi.Response(
                description="商品不存在",
                examples={
                    "application/json": {
                        "code": 404,
                        "message": "商品不存在",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['商品管理']
    )
    def get(self, request, product_id):
        try:
            service = UnifiedEcommerceService()
            product = service.get_product_detail(product_id)

            if product:
                # 将 Product 对象转换为字典
                if isinstance(product, dict):
                    product_data = product
                else:
                    product_data = {
                        'product_id': getattr(product, 'product_id', None),
                        'product_name': getattr(product, 'product_name', ''),
                        'description': getattr(product, 'description', ''),
                        'sale_price': float(getattr(product, 'sale_price', 0)),
                        'stock_quantity': getattr(product, 'stock_quantity', 0),
                        'image_urls': getattr(product, 'image_urls', []),
                        'category_id': getattr(product, 'category_id', None),
                        'category_name': getattr(product, 'category_name', ''),
                        'created_at': getattr(product, 'created_at', None),
                        'updated_at': getattr(product, 'updated_at', None),
                    }
                    # 移除空值
                    product_data = {k: v for k, v in product_data.items() if v is not None}

                return Response({
                    "code": 0,
                    "message": "success",
                    "data": product_data,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return Response({
                    "code": 404,
                    "message": "商品不存在",
                    "data": None,
                    "timestamp": datetime.now().isoformat()
                }, status=404)

        except Exception as e:
            import traceback
            print(f"获取商品详情错误: {str(e)}")
            print(traceback.format_exc())

            return Response({
                "code": 500,
                "message": f"获取商品详情失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)

    @swagger_auto_schema(
        operation_summary="编辑商品",
        operation_description="仅商品所属卖家或管理员可编辑（seller_id校验）",
        request_body=ProductUpdateSerializer,
        tags=['商品管理'],
        security=[{'Bearer': []}]
    )
    def put(self, request, product_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        serializer = ProductUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse.error(serializer.errors, 400), status=400)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            product = db.query(Product).filter(
                Product.product_id == product_id,
                Product.is_active == True
            ).first()
            if not product:
                return Response(APIResponse.error("商品不存在", 404), status=404)

            role = user_info.get("role", "normal")
            if role != "admin" and product.seller_id != user_info["user_id"]:
                return Response(APIResponse.error("无权限编辑该商品", 403), status=403)

            update_data = serializer.validated_data
            for key, value in update_data.items():
                setattr(product, key, value)
            db.commit()
            db.refresh(product)
            ProductCache.invalidate_product_caches(product_id)
            return Response(APIResponse.success(_serialize_product(product), "编辑成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"编辑失败: {str(e)}", 500), status=500)

    @swagger_auto_schema(
        operation_summary="删除商品",
        operation_description="软删除商品（seller_id校验）",
        tags=['商品管理'],
        security=[{'Bearer': []}]
    )
    def delete(self, request, product_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            product = db.query(Product).filter(
                Product.product_id == product_id,
                Product.is_active == True
            ).first()
            if not product:
                return Response(APIResponse.error("商品不存在", 404), status=404)

            role = user_info.get("role", "normal")
            if role != "admin" and product.seller_id != user_info["user_id"]:
                return Response(APIResponse.error("无权限删除该商品", 403), status=403)

            product.is_active = False
            product.is_available = False
            if hasattr(product, "status"):
                product.status = "inactive"
            db.commit()
            ProductCache.invalidate_product_caches(product_id)
            return Response(APIResponse.success(message="删除成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"删除失败: {str(e)}", 500), status=500)


class CartView(APIView):
    @swagger_auto_schema(
        operation_summary="查看购物车",
        tags=['购物车'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            items = db.query(CartItem).options(
                joinedload(CartItem.product)
            ).filter(CartItem.user_id == user_info["user_id"]).all()
            data = []
            for item in items:
                product = item.product
                if not product or not product.is_active:
                    continue
                data.append({
                    "product_id": product.product_id,
                    "product_name": product.product_name,
                    "sale_price": float(product.sale_price),
                    "stock_quantity": product.stock_quantity,
                    "quantity": item.quantity,
                    "line_total": float(product.sale_price) * item.quantity,
                })
            return Response(APIResponse.success(data))
        except Exception as e:
            return Response(APIResponse.error(f"获取购物车失败: {str(e)}", 500), status=500)

    @swagger_auto_schema(
        operation_summary="添加购物车",
        request_body=CartUpsertSerializer,
        tags=['购物车'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        serializer = CartUpsertSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse.error(serializer.errors, 400), status=400)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            product_id = serializer.validated_data["product_id"]
            quantity = serializer.validated_data["quantity"]
            product = db.query(Product).filter(
                Product.product_id == product_id,
                Product.is_active == True,
                Product.is_available == True
            ).first()
            if not product:
                return Response(APIResponse.error("商品不存在或已下架", 404), status=404)

            cart_item = db.query(CartItem).filter(
                CartItem.user_id == user_info["user_id"],
                CartItem.product_id == product_id
            ).first()
            if cart_item:
                cart_item.quantity += quantity
            else:
                cart_item = CartItem(
                    user_id=user_info["user_id"],
                    product_id=product_id,
                    quantity=quantity
                )
                db.add(cart_item)
            db.commit()
            return Response(APIResponse.success(message="添加成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"添加失败: {str(e)}", 500), status=500)


class CartItemDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="修改购物车数量",
        request_body=CartQuantitySerializer,
        tags=['购物车'],
        security=[{'Bearer': []}]
    )
    def put(self, request, product_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        serializer = CartQuantitySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse.error(serializer.errors, 400), status=400)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            cart_item = db.query(CartItem).filter(
                CartItem.user_id == user_info["user_id"],
                CartItem.product_id == product_id
            ).first()
            if not cart_item:
                exists = db.query(CartItem.cart_item_id).filter(CartItem.product_id == product_id).first()
                if exists:
                    return Response(APIResponse.error("无权限修改该购物车项", 403), status=403)
                return Response(APIResponse.error("购物车项不存在", 404), status=404)

            cart_item.quantity = serializer.validated_data["quantity"]
            db.commit()
            return Response(APIResponse.success(message="修改成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"修改失败: {str(e)}", 500), status=500)

    @swagger_auto_schema(
        operation_summary="删除购物车项",
        tags=['购物车'],
        security=[{'Bearer': []}]
    )
    def delete(self, request, product_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            cart_item = db.query(CartItem).filter(
                CartItem.user_id == user_info["user_id"],
                CartItem.product_id == product_id
            ).first()
            if not cart_item:
                exists = db.query(CartItem.cart_item_id).filter(CartItem.product_id == product_id).first()
                if exists:
                    return Response(APIResponse.error("无权限删除该购物车项", 403), status=403)
                return Response(APIResponse.error("购物车项不存在", 404), status=404)
            db.delete(cart_item)
            db.commit()
            return Response(APIResponse.success(message="删除成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"删除失败: {str(e)}", 500), status=500)


class OrderView(APIView):
    @swagger_auto_schema(
        operation_summary="从购物车生成订单",
        request_body=OrderCreateFromCartSerializer,
        tags=['订单'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        serializer = OrderCreateFromCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse.error(serializer.errors, 400), status=400)

        shipping_amount = serializer.validated_data.get("shipping_amount", Decimal("0.00"))
        discount_amount = serializer.validated_data.get("discount_amount", Decimal("0.00"))

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            affected_product_ids = set()
            cart_items = db.query(CartItem).options(
                joinedload(CartItem.product)
            ).filter(CartItem.user_id == user_info["user_id"]).all()
            if not cart_items:
                return Response(APIResponse.error("购物车为空", 400), status=400)

            subtotal = Decimal("0.00")
            normalized_items = []
            for cart_item in cart_items:
                product = cart_item.product
                if not product or not product.is_active or not product.is_available:
                    return Response(APIResponse.error(f"商品不可用: {cart_item.product_id}", 400), status=400)
                if product.stock_quantity < cart_item.quantity:
                    return Response(APIResponse.error(f"库存不足: {product.product_name}", 400), status=400)

                unit_price = Decimal(str(product.sale_price))
                line_total = unit_price * cart_item.quantity
                subtotal += line_total
                normalized_items.append({
                    "product": product,
                    "quantity": cart_item.quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "cart_item": cart_item,
                })

            total = subtotal + shipping_amount - discount_amount
            if total < Decimal("0.00"):
                total = Decimal("0.00")

            order_number = f"ORD{int(time.time() * 1000)}{secrets.randbelow(1000):03d}"
            order = Order(
                order_number=order_number,
                user_id=user_info["user_id"],
                subtotal_amount=subtotal,
                shipping_amount=shipping_amount,
                discount_amount=discount_amount,
                total_amount=total,
                order_status=OrderStatus.PENDING,
            )
            db.add(order)
            db.flush()

            for item in normalized_items:
                db.add(OrderItem(
                    order_id=order.order_id,
                    product_id=item["product"].product_id,
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total_price=item["line_total"],
                ))
                # 关键一致性：只在库存足够时扣减
                item["product"].stock_quantity -= item["quantity"]
                affected_product_ids.add(item["product"].product_id)
                db.delete(item["cart_item"])

            db.commit()
            for pid in affected_product_ids:
                ProductCache.invalidate_product_caches(pid)
            return Response(APIResponse.success({
                "order_id": order.order_id,
                "order_number": order.order_number,
                "total_amount": float(order.total_amount),
                "order_status": order.order_status.value,
                "payment_status": order.payment_status.value
            }, "下单成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"下单失败: {str(e)}", 500), status=500)

    @swagger_auto_schema(
        operation_summary="我的订单列表",
        tags=['订单'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            orders = db.query(Order).options(
                joinedload(Order.order_items).joinedload(OrderItem.product)
            ).filter(
                Order.user_id == user_info["user_id"],
                Order.is_deleted == False
            ).order_by(Order.created_at.desc()).all()
            data = []
            for order in orders:
                data.append({
                    "order_id": order.order_id,
                    "order_number": order.order_number,
                    "total_amount": float(order.total_amount),
                    "order_status": order.order_status.value,
                    "payment_status": order.payment_status.value,
                    "created_at": order.created_at,
                    "items": [
                        {
                            "product_id": it.product_id,
                            "product_name": it.product.product_name if it.product else "",
                            "quantity": it.quantity,
                            "unit_price": float(it.unit_price),
                            "total_price": float(it.total_price),
                        } for it in order.order_items
                    ]
                })
            return Response(APIResponse.success(data))
        except Exception as e:
            return Response(APIResponse.error(f"获取订单失败: {str(e)}", 500), status=500)


class OrderDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="订单详情",
        operation_description="仅订单所属用户可查看，用于IDOR防护验证",
        tags=['订单'],
        security=[{'Bearer': []}]
    )
    def get(self, request, order_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            order = db.query(Order).options(
                joinedload(Order.order_items).joinedload(OrderItem.product)
            ).filter(Order.order_id == order_id, Order.is_deleted == False).first()
            if not order:
                return Response(APIResponse.error("订单不存在", 404), status=404)

            if order.user_id != user_info["user_id"]:
                return Response(APIResponse.error("无权限查看该订单", 403), status=403)

            data = {
                "order_id": order.order_id,
                "order_number": order.order_number,
                "total_amount": float(order.total_amount),
                "order_status": order.order_status.value,
                "payment_status": order.payment_status.value,
                "created_at": order.created_at,
                "items": [
                    {
                        "product_id": it.product_id,
                        "product_name": it.product.product_name if it.product else "",
                        "quantity": it.quantity,
                        "unit_price": float(it.unit_price),
                        "total_price": float(it.total_price),
                    } for it in order.order_items
                ]
            }
            return Response(APIResponse.success(data))
        except Exception as e:
            return Response(APIResponse.error(f"获取订单详情失败: {str(e)}", 500), status=500)


class OrderCancelView(APIView):
    @swagger_auto_schema(
        operation_summary="取消订单",
        tags=['订单'],
        security=[{'Bearer': []}]
    )
    def post(self, request, order_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            affected_product_ids = set()
            # IDOR防护：必须附加当前用户条件
            order = db.query(Order).options(
                joinedload(Order.order_items).joinedload(OrderItem.product)
            ).filter(
                Order.order_id == order_id,
                Order.user_id == user_info["user_id"]
            ).first()
            if not order:
                exists = db.query(Order.order_id).filter(Order.order_id == order_id).first()
                if exists:
                    return Response(APIResponse.error("无权限取消该订单", 403), status=403)
                return Response(APIResponse.error("订单不存在", 404), status=404)
            if order.order_status == OrderStatus.CANCELLED:
                return Response(APIResponse.success(message="订单已取消"))

            refund_data = None
            if order.payment_status == PaymentStatus.PAID:
                payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()
                if not payment or not payment.gateway_transaction_id:
                    return Response(APIResponse.error("已支付订单缺少银行交易流水，无法退款", 400), status=400)
                try:
                    response = requests.post(
                        settings.BANK_REFUND_URL,
                        json={
                            "transaction_id": payment.gateway_transaction_id,
                            "order_no": order.order_number,
                            "amount": str(order.total_amount),
                        },
                        timeout=5,
                    )
                    refund_body = response.json()
                except requests.RequestException as exc:
                    return Response(APIResponse.error(f"银行退款请求失败: {str(exc)}", 502), status=502)
                except ValueError:
                    return Response(APIResponse.error("银行退款响应格式不正确", 502), status=502)
                if response.status_code >= 400 or refund_body.get("code") != 0:
                    return Response(APIResponse.error(f"银行退款失败: {refund_body.get('message', response.text)}", 400), status=400)
                payment.payment_status = PaymentStatus.REFUNDED
                payment.refund_date = datetime.now()
                order.payment_status = PaymentStatus.REFUNDED
                refund_data = refund_body.get("data")

            order.order_status = OrderStatus.CANCELLED
            order.cancelled_date = datetime.now()
            for item in order.order_items:
                if item.product:
                    item.product.stock_quantity += item.quantity
                    affected_product_ids.add(item.product.product_id)
            db.commit()
            for pid in affected_product_ids:
                ProductCache.invalidate_product_caches(pid)
            return Response(APIResponse.success({"refund": refund_data}, "取消成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"取消失败: {str(e)}", 500), status=500)


class OrderDeleteView(APIView):
    @swagger_auto_schema(
        operation_summary="删除已取消订单",
        operation_description="仅隐藏当前用户自己的已取消订单，保留数据库中的订单和支付流水记录。",
        tags=['订单'],
        security=[{'Bearer': []}]
    )
    def delete(self, request, order_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            order = db.query(Order).filter(
                Order.order_id == order_id,
                Order.user_id == user_info["user_id"],
                Order.is_deleted == False
            ).first()
            if not order:
                exists = db.query(Order.order_id).filter(Order.order_id == order_id).first()
                if exists:
                    return Response(APIResponse.error("无权限删除该订单", 403), status=403)
                return Response(APIResponse.error("订单不存在", 404), status=404)
            if order.order_status != OrderStatus.CANCELLED:
                return Response(APIResponse.error("只有已取消订单可以删除", 400), status=400)

            order.is_deleted = True
            db.commit()
            return Response(APIResponse.success(message="删除成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"删除失败: {str(e)}", 500), status=500)


class OrderBankPayView(APIView):
    @swagger_auto_schema(
        operation_summary="发起银行支付",
        operation_description="为当前用户的待支付订单生成银行支付页面跳转 URL。",
        tags=['支付'],
        security=[{'Bearer': []}]
    )
    def post(self, request, order_id):
        user_info = _get_user_info(request)
        if not user_info:
            return Response(APIResponse.error("用户未认证", 401), status=401)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            user = db.query(User).filter(User.user_id == user_info["user_id"]).first()
            if not user:
                return Response(APIResponse.error("用户不存在", 404), status=404)
            if not (user.bank_card_number or "").strip():
                return Response(APIResponse.error("请先在个人中心绑定银行卡", 400), status=400)

            order = db.query(Order).filter(
                Order.order_id == order_id,
                Order.user_id == user_info["user_id"]
            ).first()
            if not order:
                exists = db.query(Order.order_id).filter(Order.order_id == order_id).first()
                if exists:
                    return Response(APIResponse.error("无权限支付该订单", 403), status=403)
                return Response(APIResponse.error("订单不存在", 404), status=404)
            if order.order_status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
                return Response(APIResponse.error("该订单不可支付", 400), status=400)
            if order.payment_status == PaymentStatus.PAID:
                return Response(APIResponse.error("订单已支付", 400), status=400)

            amount = f"{Decimal(str(order.total_amount)):.2f}"
            params = {
                "order_no": order.order_number,
                "amount": amount,
                "merchant_id": settings.ECOMMERCE_MERCHANT_ID,
                "timestamp": str(int(time.time())),
                "return_url": settings.ECOMMERCE_PAYMENT_RETURN_URL,
                "callback_url": settings.ECOMMERCE_BANK_CALLBACK_URL,
                "account_number": user.bank_card_number,
            }
            params["signature"] = sign_payment_params(params, settings.ECOMMERCE_MERCHANT_PRIVATE_KEY)
            pay_url = f"{settings.BANK_PAY_BASE_URL.rstrip('/')}/pay?{urlencode(params)}"
            return Response(APIResponse.success({
                "pay_url": pay_url,
                "order_no": order.order_number,
                "amount": amount,
            }))
        except Exception as e:
            return Response(APIResponse.error(f"发起支付失败: {str(e)}", 500), status=500)


class BankPaymentSyncResultView(APIView):
    @swagger_auto_schema(
        operation_summary="解析银行同步支付结果",
        operation_description="前端同步跳转回电商结果页后，将 encrypted_key、iv、data 提交到后端解密展示。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["encrypted_key", "iv", "data"],
            properties={
                "transaction_id": openapi.Schema(type=openapi.TYPE_STRING, description="银行交易流水号，可选"),
                "encrypted_key": openapi.Schema(type=openapi.TYPE_STRING, description="SM2 加密后的 SM4 密钥"),
                "iv": openapi.Schema(type=openapi.TYPE_STRING, description="SM4-CBC IV"),
                "data": openapi.Schema(type=openapi.TYPE_STRING, description="SM4 加密后的支付结果正文"),
            },
        ),
        tags=["支付"],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        encrypted_key = request.data.get("encrypted_key")
        iv = request.data.get("iv")
        data = request.data.get("data")
        if not encrypted_key or not iv or not data:
            return Response(APIResponse.error("缺少 encrypted_key、iv 或 data", 400), status=400)

        try:
            result = open_result_envelope(encrypted_key, iv, data, settings.ECOMMERCE_MERCHANT_PRIVATE_KEY)
        except Exception as exc:
            return Response(APIResponse.error(f"支付结果解密失败: {str(exc)}", 400), status=400)

        return Response(APIResponse.success({
            "order_no": result.get("order_no"),
            "status": result.get("status"),
            "reason": result.get("reason", ""),
            "bank_transaction_id": result.get("bank_transaction_id") or request.data.get("transaction_id"),
            "timestamp": result.get("timestamp"),
        }))


@method_decorator(csrf_exempt, name='dispatch')
class BankPaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="银行支付异步回调",
        operation_description="接收银行发送的 encrypted_key、iv、data，使用电商 SM2 私钥解密后幂等更新订单支付状态。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["encrypted_key", "iv", "data"],
            properties={
                "transaction_id": openapi.Schema(type=openapi.TYPE_STRING, description="银行交易流水号，可选"),
                "encrypted_key": openapi.Schema(type=openapi.TYPE_STRING, description="SM2 加密后的 SM4 密钥"),
                "iv": openapi.Schema(type=openapi.TYPE_STRING, description="SM4-CBC IV"),
                "data": openapi.Schema(type=openapi.TYPE_STRING, description="SM4 加密后的支付结果正文"),
            },
        ),
        tags=["支付"],
    )
    def post(self, request):
        encrypted_key = request.data.get("encrypted_key")
        iv = request.data.get("iv")
        data = request.data.get("data")
        if not encrypted_key or not iv or not data:
            return Response(APIResponse.error("缺少 encrypted_key、iv 或 data", 400), status=400)

        merchant_private_key = settings.ECOMMERCE_MERCHANT_PRIVATE_KEY

        try:
            result = open_result_envelope(encrypted_key, iv, data, merchant_private_key)
        except Exception as exc:
            return Response(APIResponse.error(f"支付结果解密失败: {str(exc)}", 400), status=400)

        order_no = result.get("order_no")
        pay_status = result.get("status")
        bank_transaction_id = result.get("bank_transaction_id") or request.data.get("transaction_id")
        if not order_no or not pay_status or not bank_transaction_id:
            return Response(APIResponse.error("支付结果正文缺少必要字段", 400, result), status=400)

        service = UnifiedEcommerceService()
        db = service.db_session
        try:
            order = db.query(Order).filter(Order.order_number == order_no).first()
            if not order:
                return Response(APIResponse.error("订单不存在", 404, result), status=404)

            existing_payment = db.query(Payment).filter(Payment.order_id == order.order_id).first()
            target_status = PaymentStatus.PAID if pay_status == "success" else PaymentStatus.FAILED
            if (
                existing_payment
                and existing_payment.gateway_transaction_id == bank_transaction_id
                and existing_payment.payment_status == target_status
            ):
                return Response(APIResponse.success({
                    "order_no": order_no,
                    "payment_status": existing_payment.payment_status.value,
                    "idempotent": True,
                }, "回调已处理"))

            if not existing_payment:
                existing_payment = Payment(
                    transaction_id=f"PAY{int(time.time() * 1000)}{secrets.randbelow(1000):03d}",
                    order_id=order.order_id,
                    amount=order.total_amount,
                    payment_method=PaymentMethod.BANK_TRANSFER,
                    payment_gateway="mock_bank",
                )
                db.add(existing_payment)

            now = datetime.now()
            existing_payment.gateway_transaction_id = bank_transaction_id
            existing_payment.payment_status = target_status
            if target_status == PaymentStatus.PAID:
                existing_payment.payment_date = existing_payment.payment_date or now
                existing_payment.captured_date = existing_payment.captured_date or now

            order.payment_status = target_status
            if target_status == PaymentStatus.PAID and order.order_status == OrderStatus.PENDING:
                order.order_status = OrderStatus.CONFIRMED

            db.commit()
            return Response(APIResponse.success({
                "order_no": order_no,
                "order_status": order.order_status.value,
                "payment_status": order.payment_status.value,
                "bank_transaction_id": bank_transaction_id,
                "idempotent": False,
            }, "回调处理成功"))
        except Exception as e:
            db.rollback()
            return Response(APIResponse.error(f"回调处理失败: {str(e)}", 500), status=500)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="健康检查",
        operation_description="检查API服务及其依赖组件的健康状态",
        responses={
            200: openapi.Response(
                description="服务正常",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "服务正常",
                        "data": {
                            "api": "healthy",
                            "database": "healthy",
                            "redis": "healthy",
                            "timestamp": "2024-01-01T12:00:00"
                        },
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            503: openapi.Response(
                description="服务异常",
                examples={
                    "application/json": {
                        "code": 503,
                        "message": "服务异常",
                        "data": {
                            "api": "healthy",
                            "database": "unhealthy: connection failed",
                            "redis": "healthy",
                            "timestamp": "2024-01-01T12:00:00"
                        },
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['系统管理']
    )
    def get(self, request):
        """健康检查接口"""
        services_status = {
            'api': 'healthy',
            'database': 'unknown',
            'redis': 'unknown',
            'timestamp': datetime.now().isoformat()
        }

        # 检查数据库连接
        try:
            service = UnifiedEcommerceService()
            # 简单的数据库查询测试
            categories = service.get_categories()
            services_status['database'] = 'healthy'
        except Exception as e:
            services_status['database'] = f'unhealthy: {str(e)}'

        # 检查Redis连接
        try:
            if redis_client.ping():
                services_status['redis'] = 'healthy'
            else:
                services_status['redis'] = 'unhealthy: ping failed'
        except Exception as e:
            services_status['redis'] = f'unhealthy: {str(e)}'

        # 检查整体健康状态
        overall_health = all(
            status == 'healthy'
            for service, status in services_status.items()
            if service in ['api', 'database', 'redis']
        )

        return JsonResponse({
            "code": 0 if overall_health else 503,
            "message": "服务正常" if overall_health else "服务异常",
            "data": services_status,
            "timestamp": datetime.now().isoformat()
        }, status=200 if overall_health else 503)


class CacheStatusView(APIView):
    """缓存状态查看"""

    @swagger_auto_schema(
        operation_summary="缓存状态",
        operation_description="查看系统缓存和JWT黑名单状态",
        responses={
            200: openapi.Response(
                description="获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": {
                            "redis_status": "connected",
                            "jwt_blacklist": {
                                "total_tokens": 10,
                                "valid_tokens": 8,
                                "avg_ttl_minutes": 25.5
                            },
                            "timestamp": "2024-01-01T12:00:00"
                        },
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            ),
            500: openapi.Response(
                description="获取失败",
                examples={
                    "application/json": {
                        "code": 500,
                        "message": "获取缓存状态失败",
                        "data": None,
                        "timestamp": "2024-01-01T12:00:00"
                    }
                }
            )
        },
        tags=['系统管理'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        """查看缓存状态"""
        try:
            from api_service.utils.jwt_balcklist import jwt_blacklist

            # 获取黑名单信息
            blacklist_info = jwt_blacklist.get_blacklist_info()
            blacklist_size = jwt_blacklist.get_blacklist_size()

            # Redis连接状态
            redis_status = "connected" if redis_client.ping() else "disconnected"

            cache_status = {
                'redis_status': redis_status,
                'jwt_blacklist': {
                    'total_tokens': blacklist_size,
                    'valid_tokens': blacklist_info.get('valid_tokens', 0),
                    'avg_ttl_minutes': round(blacklist_info.get('avg_ttl_minutes', 0), 2)
                },
                'timestamp': datetime.now().isoformat()
            }

            return JsonResponse({
                "code": 0,
                "message": "success",
                "data": cache_status,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                "code": 500,
                "message": f"获取缓存状态失败: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }, status=500)
