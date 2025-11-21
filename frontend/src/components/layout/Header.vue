<template>
  <header class="app-header">
    <div class="header-container">
      <div class="header-left">
        <router-link to="/" class="logo" aria-label="返回首页">
          <h1>电商系统</h1>
        </router-link>
        <nav class="main-nav" aria-label="主导航">
          <!-- 只有管理员能看到控制台链接 -->
          <router-link 
            v-if="isAdmin"
            to="/" 
            class="nav-link"
          >
            控制台
          </router-link>
          <router-link to="/products" class="nav-link">商品</router-link>
          <router-link to="/navigation" class="nav-link">导航中心</router-link>
        </nav>
      </div>

      <div class="header-right">
        <div class="search-box" role="search">
          <input
            type="text"
            placeholder="搜索商品..."
            v-model="searchKeyword"
            @keyup.enter="handleSearch"
          />
          <button @click="handleSearch" class="search-btn">搜索</button>
        </div>

        <div class="user-menu" v-if="isAuthenticated">
          <div class="user-info" @click="toggleUserMenu">
            <span class="username">{{ currentUser?.username }}</span>
            <div class="avatar">{{ getInitials(currentUser?.username) }}</div>
          </div>
          
          <div v-if="showUserMenu" class="user-dropdown">
            <router-link to="/profile" class="dropdown-item">
              <i class="icon">👤</i>个人中心
            </router-link>
            <router-link to="/navigation" class="dropdown-item">
              <i class="icon">🧭</i>系统导航
            </router-link>
            <div class="dropdown-divider"></div>
            <button @click="handleLogout" class="dropdown-item logout">
              <i class="icon">🚪</i>退出登录
            </button>
          </div>
        </div>

        <div v-else class="auth-buttons">
          <router-link to="/login" class="auth-btn login">登录</router-link>
          <router-link to="/register" class="auth-btn register">注册</router-link>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import { SecurityUtils } from '../../utils/security';

export default {
  name: 'AppHeader',
  setup() {
    const store = useStore();
    const router = useRouter();
    
    const searchKeyword = ref('');
    const showUserMenu = ref(false);

    const isAuthenticated = computed(() => store.getters['auth/isAuthenticated']);
    const currentUser = computed(() => store.getters['auth/currentUser']);

    const isAdmin = computed(() => {
      return currentUser.value?.role === 'admin';
    });

    const getInitials = (username) => {
      if (!username) return 'U';
      return username.charAt(0).toUpperCase();
    };

    const handleSearch = () => {
      if (!searchKeyword.value.trim()) return;
      const sanitized = SecurityUtils.sanitizeInput(searchKeyword.value.trim());
      router.push({
        path: '/products',
        query: { keyword: sanitized }
      });
      searchKeyword.value = '';
    };

    const toggleUserMenu = () => {
      showUserMenu.value = !showUserMenu.value;
    };

    const handleLogout = async () => {
      await store.dispatch('auth/logout');
      showUserMenu.value = false;
      router.push('/');
    };

    const closeUserMenu = (event) => {
      if (!event.target.closest('.user-menu')) {
        showUserMenu.value = false;
      }
    };

    onMounted(() => {
      document.addEventListener('click', closeUserMenu);
    });

    onUnmounted(() => {
      document.removeEventListener('click', closeUserMenu);
    });

    return {
      searchKeyword,
      showUserMenu,
      isAuthenticated,
      currentUser,
      isAdmin,
      getInitials,
      handleSearch,
      toggleUserMenu,
      handleLogout
    };
  }
};
</script>

<style scoped>
.app-header {
  background: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.logo h1 {
  margin: 0;
  color: #007bff;
  font-size: 1.5rem;
  text-decoration: none;
}

.logo:hover {
  text-decoration: none;
}

.main-nav {
  display: flex;
  gap: 1.5rem;
}

.nav-link {
  color: #333;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 0;
  position: relative;
  transition: color 0.3s;
}

.nav-link:hover {
  color: #007bff;
}

.nav-link.router-link-active {
  color: #007bff;
}

.nav-link.router-link-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #007bff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.search-box {
  display: flex;
  gap: 0.5rem;
}

.search-box input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 200px;
  font-size: 0.875rem;
}

.search-box input:focus {
  outline: none;
  border-color: #007bff;
}

.search-btn {
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.search-btn:hover {
  background: #0056b3;
}

.user-menu {
  position: relative;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background: #f8f9fa;
}

.username {
  font-weight: 500;
  color: #333;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 600;
}

.user-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-width: 160px;
  margin-top: 0.5rem;
  z-index: 1000;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  color: #333;
  text-decoration: none;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background-color 0.3s;
}

.dropdown-item:hover {
  background: #f8f9fa;
}

.dropdown-item.logout {
  color: #dc3545;
}

.dropdown-divider {
  height: 1px;
  background: #e9ecef;
  margin: 0.25rem 0;
}

.auth-buttons {
  display: flex;
  gap: 0.5rem;
}

.auth-btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.3s;
}

.auth-btn.login {
  color: #007bff;
  border: 1px solid #007bff;
}

.auth-btn.login:hover {
  background: #007bff;
  color: white;
}

.auth-btn.register {
  background: #007bff;
  color: white;
  border: 1px solid #007bff;
}

.auth-btn.register:hover {
  background: #0056b3;
}

@media (max-width: 768px) {
  .header-container {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
  }

  .header-left {
    flex-direction: column;
    gap: 1rem;
    width: 100%;
  }

  .main-nav {
    justify-content: center;
  }

  .header-right {
    width: 100%;
    justify-content: center;
  }

  .search-box {
    flex: 1;
    max-width: 300px;
  }

  .search-box input {
    width: 100%;
  }
}
</style>