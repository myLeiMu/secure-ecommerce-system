from django.urls import path
from .admin_views import (MFAVerifyView, MFARebindView, OverviewView, UsersView, ProductsView,
                         CategoriesView, OrdersView, AuditView, PermissionsView)
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    PasswordChangeView, PasswordResetCodeView, PasswordResetView,
    ProductListView, ProductDetailView, HealthCheckView, CacheStatusView,
    CategoryListView, CertChallengeView, CertLoginView, CertFileLoginView, CertMTLSLoginView,
    CartView, CartItemDetailView, OrderView, OrderDetailView, OrderCancelView,
    BankCardBindView, OrderDeleteView, OrderBankPayView, BankPaymentSyncResultView, BankPaymentCallbackView
)

urlpatterns = [
    path('auth/mfa/verify', MFAVerifyView.as_view()),
    path('auth/mfa/rebind', MFARebindView.as_view()),
    path('admin/overview', OverviewView.as_view()),
    path('admin/users', UsersView.as_view()),
    path('admin/users/<int:user_id>', UsersView.as_view()),
    path('admin/products', ProductsView.as_view()),
    path('admin/products/<int:product_id>', ProductsView.as_view()),
    path('admin/categories', CategoriesView.as_view()),
    path('admin/categories/<int:category_id>', CategoriesView.as_view()),
    path('admin/orders', OrdersView.as_view()),
    path('admin/orders/<int:order_id>/ship', OrdersView.as_view()),
    path('admin/permissions', PermissionsView.as_view()),
    path('merchant/products', ProductsView.as_view()),
    path('merchant/products/<int:product_id>', ProductsView.as_view()),
    path('audit/events', AuditView.as_view()),
    path('audit/export', AuditView.as_view()),
    path('audit/permissions', PermissionsView.as_view()),
    # 用户认证
    path('auth/login', UserLoginView.as_view(), name='user-login'),
    path('auth/cert/challenge', CertChallengeView.as_view(), name='cert-challenge'),
    path('auth/cert/login', CertLoginView.as_view(), name='cert-login'),
    path('auth/cert/file-login', CertFileLoginView.as_view(), name='cert-file-login'),
    path('auth/cert/mtls-login', CertMTLSLoginView.as_view(), name='cert-mtls-login'),
    path('auth/logout', UserLogoutView.as_view(), name='user-logout'),

    # 用户管理
    path('users/register', UserRegistrationView.as_view(), name='user-register'),
    path('users/profile', UserProfileView.as_view(), name='user-profile'),
    path('users/bank-card', BankCardBindView.as_view(), name='user-bank-card'),
    path('users/change-password', PasswordChangeView.as_view(), name='user-change-password'),
    path('users/send-reset-code', PasswordResetCodeView.as_view(), name='user-send-reset-code'),
    path('users/reset-password', PasswordResetView.as_view(), name='user-reset-password'),

    # 商品管理
    path('products', ProductListView.as_view(), name='product-list'),
    path('products/<int:product_id>', ProductDetailView.as_view(), name='product-detail'),

    # 分类管理
    path('categories', CategoryListView.as_view(), name='category-list'),

    # 购物车
    path('cart', CartView.as_view(), name='cart'),
    path('cart/items/<int:product_id>', CartItemDetailView.as_view(), name='cart-item-detail'),

    # 订单
    path('orders', OrderView.as_view(), name='orders'),
    path('orders/<int:order_id>', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:order_id>/cancel', OrderCancelView.as_view(), name='order-cancel'),
    path('orders/<int:order_id>/delete', OrderDeleteView.as_view(), name='order-delete'),
    path('orders/<int:order_id>/pay', OrderBankPayView.as_view(), name='order-bank-pay'),
    path('pay/sync-result', BankPaymentSyncResultView.as_view(), name='bank-pay-sync-result'),
    path('pay/callback', BankPaymentCallbackView.as_view(), name='bank-pay-callback'),

    # 健康检查和缓存状态
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('cache/status/', CacheStatusView.as_view(), name='cache-status'),

]
