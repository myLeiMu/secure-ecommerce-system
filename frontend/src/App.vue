<template>
  <div id="app">
    <Header />

    <div class="app-layout">
      <Sidebar v-if="showSidebar" />

      <main class="main-content" :class="{ 'with-sidebar': showSidebar }">
        <router-view />
      </main>
    </div>

    <MobileNav v-if="showSidebar" />
    <Footer />

    <!-- 全局加载指示器 -->
    <div v-if="appLoading" class="global-loading">
      <LoadingSpinner />
      <p>加载中...</p>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';
import { useStore } from 'vuex';
import { useRoute } from 'vue-router';
import Header from './components/layout/Header.vue';
import Footer from './components/layout/Footer.vue';
import Sidebar from './components/layout/Sidebar.vue';
import MobileNav from './components/layout/MobileNav.vue';
import LoadingSpinner from './components/common/LoadingSpinner.vue';

const HIDE_SIDEBAR_ROUTES = ['/login', '/register', '/forgot-password'];

export default {
  name: 'App',
  components: {
    Header,
    Footer,
    Sidebar,
    MobileNav,
    LoadingSpinner
  },
  setup() {
    const store = useStore();
    const route = useRoute();

    const appLoading = computed(() => store.getters.appLoading);
    const showSidebar = computed(() => !HIDE_SIDEBAR_ROUTES.includes(route.path));

    return {
      appLoading,
      showSidebar
    };
  }
};
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f8f9fa;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-layout {
  display: flex;
  flex: 1;
  min-height: 0;
}

.main-content {
  flex: 1;
  padding: 1.5rem;
  min-height: 100%;
  background: #f5f6fa;
}

.main-content.with-sidebar {
  border-left: 1px solid #e5e7eb;
}

.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.global-loading p {
  margin-top: 1rem;
  color: #666;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .main-content {
    padding: 1rem;
  }
}

@media (max-width: 768px) {
  .app-layout {
    flex-direction: column;
  }

  .main-content {
    padding: 1rem;
    border-left: none;
  }
}
</style>