from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import exception_handler
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime
import sys
import os
from django.http import JsonResponse
from api_service.utils.jwt_balcklist import jwt_blacklist
from api_service.utils.cache_utils import ProductCache, UserCache
from api_service.utils.redis_client import redis_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.unified_service import UnifiedEcommerceService


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


class UserProfileSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True, help_text="用户ID")
    username = serializers.CharField(read_only=True, help_text="用户名")
    email = serializers.EmailField(read_only=True, help_text="邮箱")
    phone = serializers.CharField(read_only=True, help_text="手机号")
    user_role = serializers.CharField(read_only=True, help_text="用户角色")
    is_verified = serializers.BooleanField(read_only=True, help_text="是否验证")
    last_login = serializers.DateTimeField(read_only=True, help_text="最后登录时间")
    created_at = serializers.DateTimeField(read_only=True, help_text="创建时间")


class ProductListQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(required=False, help_text="搜索关键词")
    category_id = serializers.IntegerField(required=False, help_text="分类ID")
    min_price = serializers.FloatField(required=False, help_text="最低价格")
    max_price = serializers.FloatField(required=False, help_text="最高价格")


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, required=True, help_text="原密码", write_only=True)
    new_password = serializers.CharField(max_length=128, required=True, help_text="新密码", write_only=True)


class PasswordResetCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=True, help_text="手机号")


class PasswordResetSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=True, help_text="手机号")
    code = serializers.CharField(max_length=6, required=True, help_text="验证码")
    new_password = serializers.CharField(max_length=128, required=True, help_text="新密码", write_only=True)


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
                    for field in ['user_id', 'username', 'email', 'phone', 'user_role', 'is_verified', 'last_login',
                                  'created_at']:
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
                        serialized_products.append(product)
                    else:
                        # 假设 Product 对象有这些属性
                        product_dict = {
                            'product_id': getattr(product, 'product_id', None),
                            'product_name': getattr(product, 'product_name', ''),
                            'sale_price': float(getattr(product, 'sale_price', 0)),
                            'stock_quantity': getattr(product, 'stock_quantity', 0),
                            'image_urls': getattr(product, 'image_urls', []),
                            'description': getattr(product, 'description', ''),
                            'category_id': getattr(product, 'category_id', None),
                            'category_name': getattr(product, 'category_name', ''),
                        }
                        # 移除空值
                        product_dict = {k: v for k, v in product_dict.items() if v is not None}
                        serialized_products.append(product_dict)

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