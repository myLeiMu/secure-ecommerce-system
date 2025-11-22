<template>
  <div class="dashboard-page">
    <div class="dashboard-header">
      <div class="header-content">
        <h1>管理员控制台</h1>
        <p>欢迎回来，{{ currentUser?.username || '管理员' }}！</p>
        <div class="admin-badge">
          <span class="badge">管理员</span>
          <span class="last-login">最后登录: {{ formatLastLogin(currentUser?.last_login) }}</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn primary" @click="refreshData">
          <span class="btn-icon">🔄</span>
          刷新数据
        </button>
        <button class="btn secondary" @click="showSystemStats = !showSystemStats">
          <span class="btn-icon">📊</span>
          系统统计
        </button>
      </div>
    </div>

    <!-- 系统统计面板 -->
    <div v-if="showSystemStats" class="system-stats-panel">
      <h3>实时系统状态</h3>
      <div class="system-stats">
        <div class="system-stat">
          <span class="stat-label">CPU 使用率</span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: systemStats.cpu + '%' }"></div>
          </div>
          <span class="stat-value">{{ systemStats.cpu }}%</span>
        </div>
        <div class="system-stat">
          <span class="stat-label">内存使用</span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: systemStats.memory + '%' }"></div>
          </div>
          <span class="stat-value">{{ systemStats.memory }}%</span>
        </div>
        <div class="system-stat">
          <span class="stat-label">磁盘空间</span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: systemStats.disk + '%' }"></div>
          </div>
          <span class="stat-value">{{ systemStats.disk }}%</span>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-info">
          <h3>总用户数</h3>
          <p class="stat-number">{{ adminStats.totalUsers }}</p>
          <p class="stat-change">今日新增: {{ adminStats.todayNewUsers }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🛒</div>
        <div class="stat-info">
          <h3>总订单数</h3>
          <p class="stat-number">{{ adminStats.totalOrders }}</p>
          <p class="stat-change">今日订单: {{ adminStats.todayOrders }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-info">
          <h3>总销售额</h3>
          <p class="stat-number">¥{{ formatPrice(adminStats.totalRevenue) }}</p>
          <p class="stat-change">今日收入: ¥{{ formatPrice(adminStats.todayRevenue) }}</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📦</div>
        <div class="stat-info">
          <h3>商品总数</h3>
          <p class="stat-number">{{ adminStats.totalProducts }}</p>
          <p class="stat-change">库存预警: {{ adminStats.lowStockCount }}</p>
        </div>
      </div>
    </div>

    <div class="dashboard-content">
      <!-- 左侧：用户管理和最近活动 -->
      <div class="content-column">
        <div class="content-section">
          <div class="section-header">
            <h2>用户管理</h2>
            <router-link to="/admin/users" class="view-all">查看全部</router-link>
          </div>
          <div class="user-management">
            <div class="user-stats">
              <div class="user-stat">
                <span class="label">正常用户</span>
                <span class="value">{{ userStats.activeUsers }}</span>
              </div>
              <div class="user-stat">
                <span class="label">未验证</span>
                <span class="value warning">{{ userStats.unverifiedUsers }}</span>
              </div>
              <div class="user-stat">
                <span class="label">已锁定</span>
                <span class="value danger">{{ userStats.lockedUsers }}</span>
              </div>
            </div>
            <div class="recent-users">
              <h4>最近注册用户</h4>
              <div v-for="user in recentUsers" :key="user.id" class="recent-user">
                <div class="user-avatar">{{ user.username.charAt(0).toUpperCase() }}</div>
                <div class="user-info">
                  <p class="username">{{ user.username }}</p>
                  <span class="register-time">{{ user.registerTime }}</span>
                </div>
                <span :class="['user-status', user.status]">{{ user.statusText }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="content-section">
          <h2>系统活动日志</h2>
          <div class="activity-list">
            <div v-for="activity in systemActivities" :key="activity.id" class="activity-item">
              <div :class="['activity-icon', activity.type]">{{ activity.icon }}</div>
              <div class="activity-details">
                <p class="activity-text">{{ activity.text }}</p>
                <span class="activity-time">{{ activity.time }}</span>
              </div>
              <span :class="['activity-level', activity.level]">{{ activity.level }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：快捷操作和订单管理 -->
      <div class="content-column">
        <div class="content-section">
          <h2>管理员工具</h2>
          <div class="admin-tools">
            <router-link to="/admin/products" class="admin-tool">
              <span class="tool-icon">📦</span>
              <span class="tool-text">商品管理</span>
              <span class="tool-desc">管理商品信息和库存</span>
            </router-link>
            
            <router-link to="/admin/orders" class="admin-tool">
              <span class="tool-icon">🛒</span>
              <span class="tool-text">订单管理</span>
              <span class="tool-desc">处理订单和发货</span>
            </router-link>
            
            <router-link to="/admin/users" class="admin-tool">
              <span class="tool-icon">👥</span>
              <span class="tool-text">用户管理</span>
              <span class="tool-desc">管理用户账户和权限</span>
            </router-link>
            
            <router-link to="/admin/categories" class="admin-tool">
              <span class="tool-icon">📑</span>
              <span class="tool-text">分类管理</span>
              <span class="tool-desc">管理商品分类</span>
            </router-link>

            <router-link to="/admin/analytics" class="admin-tool">
              <span class="tool-icon">📊</span>
              <span class="tool-text">数据分析</span>
              <span class="tool-desc">查看销售和用户分析</span>
            </router-link>

            <router-link to="/admin/settings" class="admin-tool">
              <span class="tool-icon">⚙️</span>
              <span class="tool-text">系统设置</span>
              <span class="tool-desc">配置系统参数</span>
            </router-link>
          </div>
        </div>

        <div class="content-section">
          <div class="section-header">
            <h2>待处理订单</h2>
            <span class="badge danger">{{ pendingOrders.length }}</span>
          </div>
          <div class="pending-orders">
            <div v-for="order in pendingOrders" :key="order.id" class="pending-order">
              <div class="order-info">
                <p class="order-id">#{{ order.id }}</p>
                <p class="order-customer">{{ order.customer }}</p>
                <p class="order-amount">¥{{ formatPrice(order.amount) }}</p>
              </div>
              <div class="order-actions">
                <button class="btn small primary" @click="processOrder(order.id)">处理</button>
                <button class="btn small secondary" @click="viewOrder(order.id)">查看</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, onMounted } from 'vue';
import { useStore } from 'vuex';

export default {
  name: 'AdminDashboard',
  setup() {
    const store = useStore();
    
    const currentUser = computed(() => store.getters['auth/currentUser']);
    const showSystemStats = ref(false);

    // 管理员统计数据
    const adminStats = ref({
      totalUsers: 1247,
      todayNewUsers: 23,
      totalOrders: 5689,
      todayOrders: 45,
      totalRevenue: 1256890,
      todayRevenue: 12450,
      totalProducts: 156,
      lowStockCount: 8
    });

    // 用户统计
    const userStats = ref({
      activeUsers: 1189,
      unverifiedUsers: 45,
      lockedUsers: 13
    });

    // 系统状态
    const systemStats = ref({
      cpu: 45,
      memory: 68,
      disk: 32
    });

    // 最近注册用户
    const recentUsers = ref([
      { id: 1, username: 'john_doe', registerTime: '2分钟前', status: 'active', statusText: '正常' },
      { id: 2, username: 'jane_smith', registerTime: '5分钟前', status: 'unverified', statusText: '未验证' },
      { id: 3, username: 'mike_wilson', registerTime: '10分钟前', status: 'active', statusText: '正常' },
      { id: 4, username: 'sara_brown', registerTime: '15分钟前', status: 'locked', statusText: '已锁定' }
    ]);

    // 系统活动日志
    const systemActivities = ref([
      {
        id: 1,
        icon: '🔒',
        text: '用户登录失败次数过多，账户已自动锁定',
        time: '2分钟前',
        type: 'security',
        level: 'warning'
      },
      {
        id: 2,
        icon: '📦',
        text: '商品库存预警：iPhone 13 库存低于阈值',
        time: '5分钟前',
        type: 'inventory',
        level: 'warning'
      },
      {
        id: 3,
        icon: '💰',
        text: '新订单支付成功 #ORD202400125',
        time: '10分钟前',
        type: 'order',
        level: 'info'
      },
      {
        id: 4,
        icon: '👥',
        text: '新用户注册成功：alex_johnson',
        time: '15分钟前',
        type: 'user',
        level: 'info'
      },
      {
        id: 5,
        icon: '🔄',
        text: '系统数据备份完成',
        time: '30分钟前',
        type: 'system',
        level: 'info'
      }
    ]);

    // 待处理订单
    const pendingOrders = ref([
      { id: 'ORD202400125', customer: '张先生', amount: 5999, status: 'pending' },
      { id: 'ORD202400124', customer: '李女士', amount: 4299, status: 'pending' },
      { id: 'ORD202400123', customer: '王先生', amount: 2999, status: 'pending' }
    ]);

    const refreshData = () => {
      // 模拟刷新数据
      console.log('刷新管理员数据...');
    };

    const processOrder = (orderId) => {
      console.log('处理订单:', orderId);
    };

    const viewOrder = (orderId) => {
      console.log('查看订单:', orderId);
    };

    const formatPrice = (price) => {
      return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    };

    const formatLastLogin = (date) => {
      if (!date) return '未知';
      return new Date(date).toLocaleString('zh-CN');
    };

    onMounted(() => {
      // 可以在这里加载真实的管理员数据
      console.log('管理员控制台已加载');
    });

    return {
      currentUser,
      showSystemStats,
      adminStats,
      userStats,
      systemStats,
      recentUsers,
      systemActivities,
      pendingOrders,
      refreshData,
      processOrder,
      viewOrder,
      formatPrice,
      formatLastLogin
    };
  }
};
</script>

<style scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid #e9ecef;
}

.header-content h1 {
  margin: 0 0 0.5rem;
  color: #2c3e50;
  font-size: 2.2rem;
  font-weight: 700;
}

.header-content p {
  margin: 0 0 0.75rem;
  color: #6c757d;
  font-size: 1.1rem;
}

.admin-badge {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.badge {
  background: #007bff;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.last-login {
  font-size: 0.875rem;
  color: #6c757d;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn.primary {
  background: #007bff;
  color: white;
}

.btn.secondary {
  background: #6c757d;
  color: white;
}

.btn.small {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.system-stats-panel {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.system-stats-panel h3 {
  margin: 0 0 1rem;
  color: #2c3e50;
}

.system-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.system-stat {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-label {
  min-width: 80px;
  color: #6c757d;
  font-size: 0.875rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #28a745;
  transition: width 0.3s;
}

.stat-value {
  min-width: 40px;
  text-align: right;
  font-weight: 600;
  color: #2c3e50;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.3s;
  border-left: 4px solid #007bff;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  font-size: 2.5rem;
  width: 70px;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #007bff, #0056b3);
  border-radius: 12px;
  color: white;
}

.stat-info h3 {
  margin: 0 0 0.5rem;
  color: #6c757d;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
}

.stat-number {
  margin: 0 0 0.25rem;
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
}

.stat-change {
  margin: 0;
  font-size: 0.875rem;
  color: #28a745;
  font-weight: 500;
}

.dashboard-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
}

.content-column {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.content-section {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.25rem;
  font-weight: 600;
}

.view-all {
  color: #007bff;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
}

.user-management {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.user-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.user-stat {
  text-align: center;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.user-stat .label {
  display: block;
  color: #6c757d;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.user-stat .value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #28a745;
}

.user-stat .value.warning {
  color: #ffc107;
}

.user-stat .value.danger {
  color: #dc3545;
}

.recent-users h4 {
  margin: 0 0 1rem;
  color: #2c3e50;
  font-size: 1rem;
}

.recent-user {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border-bottom: 1px solid #e9ecef;
}

.recent-user:last-child {
  border-bottom: none;
}

.user-avatar {
  width: 36px;
  height: 36px;
  background: #007bff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.user-info {
  flex: 1;
}

.username {
  margin: 0 0 0.25rem;
  font-weight: 600;
  color: #2c3e50;
}

.register-time {
  font-size: 0.75rem;
  color: #6c757d;
}

.user-status {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-weight: 600;
}

.user-status.active {
  background: #d4edda;
  color: #155724;
}

.user-status.unverified {
  background: #fff3cd;
  color: #856404;
}

.user-status.locked {
  background: #f8d7da;
  color: #721c24;
}

.admin-tools {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.admin-tool {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  text-decoration: none;
  color: #2c3e50;
  transition: all 0.3s;
  text-align: center;
}

.admin-tool:hover {
  background: #007bff;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.tool-icon {
  font-size: 2rem;
}

.tool-text {
  font-weight: 600;
  font-size: 1rem;
}

.tool-desc {
  font-size: 0.75rem;
  opacity: 0.8;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  transition: background-color 0.3s;
}

.activity-item:hover {
  background: #e9ecef;
}

.activity-icon {
  font-size: 1.2rem;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 8px;
  flex-shrink: 0;
}

.activity-icon.security {
  background: #fff3cd;
  color: #856404;
}

.activity-icon.inventory {
  background: #ffeaa7;
  color: #e17055;
}

.activity-icon.order {
  background: #d1ecf1;
  color: #0c5460;
}

.activity-icon.user {
  background: #d4edda;
  color: #155724;
}

.activity-icon.system {
  background: #e2e3e5;
  color: #383d41;
}

.activity-details {
  flex: 1;
}

.activity-text {
  margin: 0 0 0.25rem;
  color: #2c3e50;
  font-weight: 500;
}

.activity-time {
  font-size: 0.75rem;
  color: #6c757d;
}

.activity-level {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.activity-level.info {
  background: #d1ecf1;
  color: #0c5460;
}

.activity-level.warning {
  background: #fff3cd;
  color: #856404;
}

.pending-orders {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pending-order {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #ffc107;
}

.order-info p {
  margin: 0.25rem 0;
}

.order-id {
  font-weight: 600;
  color: #2c3e50;
}

.order-customer {
  color: #6c757d;
  font-size: 0.875rem;
}

.order-amount {
  color: #28a745;
  font-weight: 600;
}

.order-actions {
  display: flex;
  gap: 0.5rem;
}

.badge.danger {
  background: #dc3545;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

@media (max-width: 1024px) {
  .dashboard-content {
    grid-template-columns: 1fr;
  }
  
  .admin-tools {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .user-stats {
    grid-template-columns: 1fr;
  }
  
  .system-stats {
    grid-template-columns: 1fr;
  }
}
</style>