<template>
  <aside
    :class="['sidebar', { 'collapsed': collapsed }]"
    aria-label="系统导航侧边栏"
  >
    <button @click="toggleSidebar" class="sidebar-toggle">
      {{ collapsed ? '→' : '←' }}
    </button>
    
    <nav class="sidebar-nav">
      <router-link to="/products" class="nav-item">
        <span class="icon" aria-hidden="true">🛍️</span>
        <span class="text">商品模块</span>
      </router-link>
      <router-link to="/cart" class="nav-item">
        <span class="icon" aria-hidden="true">🛒</span>
        <span class="text">购物车</span>
      </router-link>
      <router-link to="/orders" class="nav-item">
        <span class="icon" aria-hidden="true">📦</span>
        <span class="text">我的订单</span>
      </router-link>
      <router-link to="/profile" class="nav-item">
        <span class="icon" aria-hidden="true">👤</span>
        <span class="text">个人中心</span>
      </router-link>
    </nav>
  </aside>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'AppSidebar',
  setup() {
    const collapsed = ref(false);
    
    const toggleSidebar = () => {
      collapsed.value = !collapsed.value;
    };
    
    return {
      collapsed,
      toggleSidebar
    };
  }
};
</script>

<style scoped>
.sidebar {
  width: 240px;
  background: #1f2937;
  color: white;
  transition: width 0.3s;
  position: sticky;
  top: 80px;
  align-self: flex-start;
  min-height: calc(100vh - 80px);
  z-index: 10;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-toggle {
  position: absolute;
  top: 1rem;
  right: -15px;
  background: #34495e;
  border: none;
  color: white;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.sidebar-nav {
  padding: 3rem 1rem 2rem;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  color: #d1d5db;
  text-decoration: none;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  transition: all 0.3s;
}

.nav-item:hover {
  background: #374151;
  color: white;
}

.nav-item.router-link-active {
  background: #2563eb;
  color: white;
}

.icon {
  font-size: 1.2rem;
  margin-right: 1rem;
  min-width: 20px;
  text-align: center;
}

.text {
  white-space: nowrap;
  transition: opacity 0.3s;
}

.sidebar.collapsed .text {
  opacity: 0;
  width: 0;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.75rem;
}

.sidebar.collapsed .icon {
  margin-right: 0;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}
</style>
