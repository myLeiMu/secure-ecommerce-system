<template>
  <nav class="mobile-nav" aria-label="移动端主导航">
    <router-link to="/" class="nav-item">
      <span class="icon">🏠</span>
      <span class="label">首页</span>
    </router-link>
    <router-link to="/products" class="nav-item">
      <span class="icon">🛍️</span>
      <span class="label">商品</span>
    </router-link>
    <router-link to="/navigation" class="nav-item">
      <span class="icon">🧭</span>
      <span class="label">导航</span>
    </router-link>
    <router-link to="/profile" class="nav-item">
      <span class="icon">👤</span>
      <span class="label">我</span>
    </router-link>
  </nav>
</template>

<script>
export default {
  name: 'MobileNav'
};
</script>

<style scoped>
.mobile-nav {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #e5e7eb;
  display: none;
  justify-content: space-around;
  padding: 0.5rem;
  z-index: 998;
  box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.05);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  color: #6b7280;
  font-size: 0.75rem;
  font-weight: 500;
}

.nav-item .icon {
  font-size: 1.25rem;
  margin-bottom: 0.25rem;
}

.nav-item.router-link-active {
  color: #2563eb;
}

@media (max-width: 768px) {
  .mobile-nav {
    display: flex;
  }
}
</style>

