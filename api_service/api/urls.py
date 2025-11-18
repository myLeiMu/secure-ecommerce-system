from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    ProductListView, ProductDetailView, HealthCheckView, CacheStatusView
)

urlpatterns = [
    # 用户认证
    path('auth/login', UserLoginView.as_view(), name='user-login'),
    path('auth/logout', UserLogoutView.as_view(), name='user-logout'),

    # 用户管理
    path('users/register', UserRegistrationView.as_view(), name='user-register'),
    path('users/profile', UserProfileView.as_view(), name='user-profile'),

    # 商品管理
    path('products', ProductListView.as_view(), name='product-list'),
    path('products/<int:product_id>', ProductDetailView.as_view(), name='product-detail'),

    # 健康检查和缓存状态（新增）
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('cache/status/', CacheStatusView.as_view(), name='cache-status'),

]