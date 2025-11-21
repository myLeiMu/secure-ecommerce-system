import { createRouter, createWebHistory } from 'vue-router';

// 页面组件
import Login from '../pages/auth/Login.vue';
import Register from '../pages/auth/Register.vue';
import ForgotPassword from '../pages/auth/ForgotPassword.vue';
import Profile from '../pages/user/Profile.vue';
import ProductList from '../pages/products/ProductList.vue';
import ProductDetail from '../pages/products/ProductDetail.vue';
import Dashboard from '../pages/dashboard/Dashboard.vue';
import SystemNavigation from '../pages/navigation/SystemNavigation.vue';
import store from '../store';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: ForgotPassword,
    meta: { requiresGuest: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  },
  {
    path: '/products',
    name: 'ProductList',
    component: ProductList
  },
  {
    path: '/products/:id',
    name: 'ProductDetail',
    component: ProductDetail
  },
  {
    path: '/navigation',
    name: 'SystemNavigation',
    component: SystemNavigation,
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const isAuthenticated = store.getters['auth/isAuthenticated'];

  // 刷新后如果有token但还未拉取用户信息，则自动同步一次
  if (isAuthenticated && !store.getters['auth/currentUser']) {
    try {
      await store.dispatch('auth/fetchProfile', { silent: true });
    } catch (error) {
      await store.dispatch('auth/logout');
    }
  }

  if (to.meta.requiresAuth && !isAuthenticated) {
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    });
  } else if (to.meta.requiresGuest && isAuthenticated) {
    next('/');
  } else {
    next();
  }
});

export default router;