"""Management endpoints use allowlisted serializers and bounded database queries."""
import json
import base64
import secrets
import time
from datetime import datetime
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from sqlalchemy import func, or_
from src.Data_base.database import SessionLocal
from src.Data_base.models.user import User
from src.Data_base.models.product import Product, Category
from src.Data_base.models.order import Order, OrderStatus, PaymentStatus
from src.Data_base.models.security import LoginChallenge, AuditEvent
from api_service.utils.cache_utils import ProductCache, UserCache
from .security_core import (ROLES, PERMISSIONS, state_for, digest, verify_factor, cipher,
                            login_data, audit)


def ok(data=None, message='操作成功'):
    return Response({'code': 0, 'message': message, 'data': data})


def fail(message, status=400):
    return Response({'code': status, 'message': message, 'data': None}, status=status)


def value(v):
    if isinstance(v, datetime):
        return v.isoformat() + 'Z'
    if isinstance(v, Decimal):
        return str(v)
    return getattr(v, 'value', v)


def fields(row, names):
    return {name: value(getattr(row, name)) for name in names.split()}


def page(query, request, serialize):
    try:
        number = max(1, int(request.query_params.get('page', 1)))
        size = min(100, max(1, int(request.query_params.get('page_size', 20))))
    except ValueError:
        raise serializers.ValidationError('分页参数必须为整数')
    total = query.count()
    return {'items': [serialize(row) for row in query.offset((number - 1) * size).limit(size)],
            'total': total, 'page': number, 'page_size': size}


class ProtectedView(APIView):
    roles = ('admin',)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from rest_framework.exceptions import PermissionDenied
        if getattr(request, 'user_info', {}).get('role') not in self.roles:
            raise PermissionDenied('当前角色无权执行此操作')


class MFAVerifyView(APIView):
    def post(self, request):
        challenge = request.data.get('challenge', '')
        code = request.data.get('code', '')
        if not isinstance(challenge, str) or len(challenge) > 100 or not isinstance(code, str) or len(code) > 64:
            return fail('验证参数无效')
        with SessionLocal.begin() as db:
            pending = db.get(LoginChallenge, digest(challenge))
            if not pending or pending.expires_at < int(time.time()):
                return fail('验证会话已过期，请重新登录', 400)
            user = db.query(User).filter_by(user_id=pending.user_id).with_for_update().first()
            state = state_for(db, pending.user_id)
            # Re-read after acquiring the per-user lock: concurrent requests cannot reuse a challenge.
            pending = db.query(LoginChallenge).filter_by(challenge_hash=digest(challenge)).populate_existing().with_for_update().first()
            if not pending:
                return fail('验证会话已使用，请重新登录', 400)
            if not user or not user.is_active or state.version != pending.version:
                return fail('验证会话失效，请重新登录', 400)
            info = {'user_id': user.user_id, 'username': user.username, 'role': user.user_role.lower()}
            if state.locked_until > int(time.time()):
                return fail('验证失败次数过多，请15分钟后重试', 429)
            previous_step = state.last_step
            if pending.pending_secret:
                state.last_step = -1
            if not verify_factor(state, code, pending.pending_secret):
                state.last_step = previous_step
                audit(db, request, 'auth.mfa.failed', result='denied', user=info)
                return fail('验证码无效、已使用或超出时间窗口', 400)
            recovery_codes = None
            if pending.pending_secret:
                state.secret = pending.pending_secret
                state.enabled = True
                recovery_codes = [secrets.token_hex(10) for _ in range(8)]
                state.recovery_hashes = json.dumps([digest(c) for c in recovery_codes])
                audit(db, request, 'auth.mfa.enroll', user=info)
            db.delete(pending)
            audit(db, request, 'auth.mfa.verify', user=info)
            data = login_data(user, state, mfa=True)
            if recovery_codes:
                data['recovery_codes'] = recovery_codes
            return ok(data)


class MFARebindView(ProtectedView):
    roles = ('admin', 'auditor')

    def post(self, request):
        from urllib.parse import quote
        with SessionLocal.begin() as db:
            user = db.query(User).filter_by(user_id=request.user_info['user_id']).with_for_update().one()
            state = state_for(db, user.user_id)
            code = request.data.get('code')
            if not isinstance(code, str) or not state.enabled or not verify_factor(state, code):
                audit(db, request, 'auth.mfa.rebind.denied', result='denied')
                return fail('请使用未使用的动态码或恢复码验证当前设备')
            state.version += 1
            secret = base64.b32encode(secrets.token_bytes(20)).decode()
            challenge = secrets.token_urlsafe(32)
            db.query(LoginChallenge).filter_by(user_id=user.user_id).delete(synchronize_session=False)
            db.add(LoginChallenge(challenge_hash=digest(challenge), user_id=user.user_id,
                                 version=state.version, expires_at=int(time.time()) + 300,
                                 pending_secret=cipher().encrypt(secret.encode()).decode()))
            audit(db, request, 'auth.mfa.rebind.start')
            return ok({'challenge': challenge, 'secret': secret,
                       'provisioning_uri': f'otpauth://totp/{quote("SecureShop:" + user.username)}?secret={secret}&issuer=SecureShop&digits=6&period=30'})


class OverviewView(ProtectedView):
    def get(self, request):
        with SessionLocal.begin() as db:
            return ok({'users': db.query(User).count(),
                       'products': db.query(Product).filter_by(is_active=True).count(),
                       'orders': db.query(Order).count(),
                       'paid_total': str(db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(Order.payment_status == PaymentStatus.PAID).scalar()),
                       'pending_shipments': db.query(Order).filter(Order.payment_status == PaymentStatus.PAID, Order.order_status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])).count(),
                       'low_stock': db.query(Product).filter(Product.is_active == True, Product.stock_quantity < 10).count()})


class UserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ROLES, required=False)
    is_active = serializers.BooleanField(required=False)


class UsersView(ProtectedView):
    def get(self, request):
        with SessionLocal.begin() as db:
            query = db.query(User)
            keyword = request.query_params.get('q', '')[:100]
            if keyword:
                query = query.filter(or_(User.username.contains(keyword, autoescape=True), User.email.contains(keyword, autoescape=True)))
            role = request.query_params.get('role')
            if role:
                query = query.filter(User.user_role == role)
            return ok(page(query.order_by(User.user_id.desc()), request,
                           lambda u: fields(u, 'user_id username email user_role is_active is_verified last_login created_at')))

    def patch(self, request, user_id):
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data:
            return fail('请选择需要修改的字段')
        if user_id == request.user_info['user_id']:
            return fail('不能修改自己的角色或停用自己的账号')
        with SessionLocal.begin() as db:
            # Serialize administrator changes so concurrent demotions cannot remove
            # every active administrator after both requests passed middleware.
            admins = db.query(User).filter(User.user_role.in_(('admin', 'ADMIN'))).order_by(User.user_id).with_for_update().all()
            actor = next((u for u in admins if u.user_id == request.user_info['user_id'] and u.is_active), None)
            if actor is None:
                return fail('管理员权限已发生变化，请重新登录', 403)
            user = db.query(User).filter_by(user_id=user_id).with_for_update().first()
            if not user:
                return fail('用户不存在', 404)
            if 'role' in data:
                user.user_role = data['role']
            if 'is_active' in data:
                user.is_active = data['is_active']
            state_for(db, user_id).version += 1
            audit(db, request, 'users.update', f'user:{user_id}')
        UserCache.invalidate_user_caches()
        return ok(message='用户已更新，原有会话已失效')


class ProductSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    product_name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    stock_quantity = serializers.IntegerField(min_value=0, max_value=100000000)
    category_id = serializers.IntegerField(min_value=1)
    seller_id = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(choices=('active', 'inactive'), required=False)
    image_urls = serializers.ListField(child=serializers.URLField(), max_length=8, required=False)


class ProductsView(ProtectedView):
    roles = ('admin', 'normal', 'merchant')

    def get(self, request):
        with SessionLocal.begin() as db:
            query = db.query(Product)
            if request.user_info['role'] in ('normal', 'merchant'):
                query = query.filter_by(seller_id=request.user_info['user_id'])
            keyword = request.query_params.get('q', '')[:100]
            if keyword:
                query = query.filter(or_(Product.product_name.contains(keyword, autoescape=True), Product.sku.contains(keyword, autoescape=True)))
            if request.query_params.get('status'):
                query = query.filter_by(status=request.query_params['status'])
            return ok(page(query.order_by(Product.product_id.desc()), request,
                           lambda p: fields(p, 'product_id sku product_name description sale_price stock_quantity category_id seller_id status image_urls')))

    def post(self, request):
        return self.save(request)

    def put(self, request, product_id):
        return self.save(request, product_id)

    def save(self, request, product_id=None):
        serializer = ProductSerializer(data=request.data, partial=product_id is not None)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with SessionLocal.begin() as db:
            product = db.query(Product).filter_by(product_id=product_id).with_for_update().first() if product_id else Product()
            if not product:
                return fail('商品不存在', 404)
            merchant = request.user_info['role'] in ('normal', 'merchant')
            if product_id and merchant and product.seller_id != request.user_info['user_id']:
                return fail('无权修改其他用户的商品', 403)
            if merchant:
                data['seller_id'] = request.user_info['user_id']
            if 'seller_id' in data:
                seller = db.get(User, data['seller_id'])
                if not seller or not seller.is_active or seller.user_role.lower() not in ('normal', 'merchant', 'admin'):
                    return fail('所属卖家不存在、已停用或角色不正确')
            if 'category_id' in data:
                category = db.get(Category, data['category_id'])
                if not category or not category.is_active:
                    return fail('请选择有效分类')
            if 'sku' in data and db.query(Product).filter(Product.sku == data['sku'], Product.product_id != (product_id or 0)).first():
                return fail('SKU已存在')
            for key, val in data.items():
                setattr(product, key, val)
            if not product_id:
                product.seller_id = data.get('seller_id', request.user_info['user_id'])
            product.status = data.get('status', product.status or 'active')
            product.is_active = product.is_available = product.status == 'active'
            db.add(product)
            db.flush()
            audit(db, request, 'products.update' if product_id else 'products.create', f'product:{product.product_id}')
        ProductCache.invalidate_product_caches(product_id)
        return ok()


class CategorySerializer(serializers.Serializer):
    category_name = serializers.CharField(max_length=100)
    sort_order = serializers.IntegerField(required=False, min_value=0)
    is_active = serializers.BooleanField(required=False)


class CategoriesView(ProtectedView):
    def get(self, request):
        with SessionLocal.begin() as db:
            return ok([fields(c, 'category_id category_name sort_order is_active') for c in db.query(Category).order_by(Category.sort_order, Category.category_id)])

    def post(self, request):
        return self.save(request)

    def put(self, request, category_id):
        return self.save(request, category_id)

    def save(self, request, category_id=None):
        serializer = CategorySerializer(data=request.data, partial=category_id is not None)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with SessionLocal.begin() as db:
            item = db.get(Category, category_id) if category_id else Category()
            if not item:
                return fail('分类不存在', 404)
            if 'category_name' in data and db.query(Category).filter(Category.category_name == data['category_name'], Category.category_id != (category_id or 0)).first():
                return fail('分类名称已存在')
            if data.get('is_active') is False and db.query(Product).filter_by(category_id=category_id, is_active=True).first():
                return fail('请先下架该分类中的商品')
            for key, val in data.items():
                setattr(item, key, val)
            db.add(item)
            db.flush()
            audit(db, request, 'categories.update', f'category:{item.category_id}')
        ProductCache.invalidate_product_caches()
        return ok()


class OrdersView(ProtectedView):
    def get(self, request):
        with SessionLocal.begin() as db:
            query = db.query(Order)
            if request.query_params.get('q'):
                query = query.filter(Order.order_number.contains(request.query_params['q'][:100], autoescape=True))
            status = request.query_params.get('status')
            if status:
                if status not in [s.value for s in OrderStatus]:
                    return fail('订单状态无效')
                query = query.filter(Order.order_status == OrderStatus(status))
            return ok(page(query.order_by(Order.order_id.desc()), request,
                           lambda o: fields(o, 'order_id order_number user_id total_amount order_status payment_status tracking_number order_date')))

    def post(self, request, order_id):
        tracking = request.data.get('tracking_number', '')
        if not isinstance(tracking, str) or not 1 <= len(tracking.strip()) <= 100:
            return fail('请输入有效物流单号')
        with SessionLocal.begin() as db:
            order = db.query(Order).filter_by(order_id=order_id).with_for_update().first()
            if not order:
                return fail('订单不存在', 404)
            if order.payment_status != PaymentStatus.PAID or order.order_status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING):
                return fail('仅已付款且未发货的订单可以发货', 409)
            order.order_status = OrderStatus.SHIPPED
            order.tracking_number = tracking.strip()
            order.shipped_date = datetime.utcnow()
            audit(db, request, 'orders.ship', f'order:{order_id}')
        return ok(message='发货成功')


class AuditView(ProtectedView):
    roles = ('admin', 'auditor')

    def get(self, request):
        with SessionLocal.begin() as db:
            query = db.query(AuditEvent)
            for name in ('action', 'result', 'role'):
                if request.query_params.get(name):
                    query = query.filter(getattr(AuditEvent, name) == request.query_params[name][:100])
            if request.query_params.get('q'):
                query = query.filter(AuditEvent.resource.contains(request.query_params['q'][:100], autoescape=True))
            if request.query_params.get('since'):
                try:
                    query = query.filter(AuditEvent.created_at >= datetime.strptime(request.query_params['since'], '%Y-%m-%d'))
                except ValueError:
                    return fail('开始日期格式应为 YYYY-MM-DD')
            serialize = lambda event: fields(event, 'event_id user_id username role action resource result ip created_at')
            query = query.order_by(AuditEvent.event_id.desc())
            export = request.path.endswith('/export')
            if export:
                from django.http import HttpResponse
                rows = [serialize(e) for e in query.limit(10000)]
                response = HttpResponse(json.dumps({'events': rows, 'limit': 10000}, ensure_ascii=False), content_type='application/json')
                response['Content-Disposition'] = 'attachment; filename="audit-report.json"'
            else:
                response = ok(page(query, request, serialize))
            audit(db, request, 'audit.export' if export else 'audit.read')
            return response


class PermissionsView(ProtectedView):
    roles = ('admin', 'auditor', 'merchant')

    def get(self, request):
        return ok(PERMISSIONS)
