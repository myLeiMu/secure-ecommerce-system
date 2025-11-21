<template>
  <div class="navigation-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">System Navigation</p>
        <h1>系统导航中心</h1>
        <p class="subtitle">依据实验4 & 6 的业务流程，统一管理顶部导航、侧边栏、面包屑与移动端快捷入口，确保用户在不同终端都能便捷操作。</p>
      </div>
      <div class="header-actions">
        <router-link to="/products" class="btn primary">前往商品模块</router-link>
        <router-link to="/profile" class="btn outline">进入个人中心</router-link>
      </div>
    </header>

    <section class="navigation-grid">
      <article class="nav-card">
        <h2>顶部导航（Header）</h2>
        <p>突出业务主入口，结合搜索与用户菜单，实现跨模块跳转。</p>
        <ul>
          <li>Logo + 关键模块（控制台 / 商品 / 导航中心）</li>
          <li>全局搜索：支持关键字过滤，阻断 XSS</li>
          <li>用户菜单：个人中心、系统导航、退出登录</li>
        </ul>
      </article>

      <article class="nav-card">
        <h2>侧边栏（Sidebar）</h2>
        <p>映射实验6 的模块划分，实现角色可扩展的纵向导航。</p>
        <ul>
          <li>控制台、商品模块、导航中心、个人中心</li>
          <li>支持折叠，桌面端粘性定位，移动端自动收起</li>
          <li>所有链接均指向实际存在的页面，避免死链</li>
        </ul>
      </article>

      <article class="nav-card">
        <h2>面包屑 & 辅助导航</h2>
        <p>在详情页（如商品详情）按用例路径展示当前位置，提供快速返回。</p>
        <ul>
          <li>首页 / 列表 / 详情的逐级反馈</li>
          <li>结合页面操作按钮（如快捷操作、重试）</li>
          <li>错误状态保留重试通道，避免流程中断</li>
        </ul>
      </article>

      <article class="nav-card">
        <h2>移动端底部导航</h2>
        <p>同一套业务节点，通过 MobileNav 提供触控友好的入口。</p>
        <ul>
          <li>首页、商品、导航中心、个人中心</li>
          <li>固定在底部并与桌面端导航保持一致</li>
          <li>命中 WCAG 触控尺寸要求（最小44px）</li>
        </ul>
      </article>
    </section>

    <section class="responsive-section">
      <h2>响应式断点 & 适配策略</h2>
      <div class="responsive-grid">
        <div v-for="breakpoint in breakpoints" :key="breakpoint.label" class="responsive-card">
          <p class="bp-label">{{ breakpoint.label }}</p>
          <p class="bp-size">{{ breakpoint.size }}</p>
          <ul>
            <li v-for="item in breakpoint.items" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="safety-section">
      <h2>安全与体验强化</h2>
      <div class="safety-grid">
        <article class="safety-card" v-for="item in safetyChecklist" :key="item.title">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <ul>
            <li v-for="point in item.points" :key="point">{{ point }}</li>
          </ul>
        </article>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'SystemNavigation',
  setup() {
    const breakpoints = [
      {
        label: '移动端',
        size: '≤ 768px',
        items: ['隐藏侧边栏，启用底部导航', '表单字体固定16px，避免缩放', '按钮全宽排列，提升触控命中率']
      },
      {
        label: '平板端',
        size: '769px - 1024px',
        items: ['侧边栏可折叠', '内容区改为单列布局', '图表与列表自动换行']
      },
      {
        label: '桌面端',
        size: '≥ 1025px',
        items: ['侧边栏粘性定位', '多列卡片布局', '大屏展示更多统计信息']
      }
    ];

    const safetyChecklist = [
      {
        title: '输入与导航安全',
        description: '所有用户输入都通过 SecurityUtils 过滤，防止 XSS / SQL 注入。',
        points: ['搜索框、表单统一使用 sanitizeInput', '导航链接只指向受控路由', '未登录用户无法访问受限路由']
      },
      {
        title: '状态管理',
        description: 'Vuex 负责持久化用户状态，App 启动时自动拉取 Profile，实现“自动刷新会话”。',
        points: ['刷新后保留登录状态', '401 自动登出并回到登录页', '10 分钟一次静默会话校验']
      },
      {
        title: '用户体验',
        description: '加载指示器、错误提示、重试入口覆盖全局，保证交互连续性。',
        points: ['LoadingSpinner 全局可见', 'ErrorMessage 提供重试回调', '移动端/桌面端一致的导航语义']
      }
    ];

    return {
      breakpoints,
      safetyChecklist
    };
  }
};
</script>

<style scoped>
.navigation-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: center;
  background: white;
  padding: 2rem;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

.eyebrow {
  text-transform: uppercase;
  font-size: 0.875rem;
  letter-spacing: 0.1em;
  color: #2563eb;
  margin-bottom: 0.25rem;
}

.page-header h1 {
  margin: 0 0 0.5rem;
  font-size: 2.2rem;
  color: #0f172a;
}

.subtitle {
  margin: 0;
  color: #475569;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  border: 1px solid transparent;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn.primary {
  background: #2563eb;
  color: white;
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
}

.btn.outline {
  border-color: #2563eb;
  color: #2563eb;
}

.btn:hover {
  transform: translateY(-2px);
}

.navigation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.5rem;
}

.nav-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
  border-top: 4px solid #2563eb;
}

.nav-card h2 {
  margin: 0 0 0.5rem;
  color: #0f172a;
}

.nav-card p {
  color: #475569;
  margin-bottom: 0.75rem;
}

.nav-card ul {
  margin: 0;
  padding-left: 1.25rem;
  color: #1e293b;
}

.responsive-section,
.safety-section {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
}

.responsive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
  margin-top: 1.5rem;
}

.responsive-card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
}

.bp-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2563eb;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.bp-size {
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0.25rem 0 0.75rem;
  color: #0f172a;
}

.responsive-card ul {
  padding-left: 1.2rem;
  color: #475569;
  margin: 0;
}

.safety-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.safety-card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1.5rem;
  border-left: 4px solid #22c55e;
}

.safety-card h3 {
  margin: 0 0 0.5rem;
  color: #0f172a;
}

.safety-card p {
  margin: 0 0 0.75rem;
  color: #475569;
}

.safety-card ul {
  margin: 0;
  padding-left: 1.2rem;
  color: #1e293b;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .navigation-page {
    padding: 1.5rem 0.5rem 2rem;
  }
}
</style>

