<template>
  <div class="dashboard-page">
    <div class="dashboard-header">
      <h1>控制台</h1>
      <p>欢迎回来，{{ currentUser?.username || '用户' }}！</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-info">
          <h3>今日访问</h3>
          <p class="stat-number">1,234</p>
          <p class="stat-change">↑ 12% 较昨日</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🛒</div>
        <div class="stat-info">
          <h3>订单数量</h3>
          <p class="stat-number">56</p>
          <p class="stat-change">↑ 8% 较上周</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-info">
          <h3>销售额</h3>
          <p class="stat-number">¥12,345</p>
          <p class="stat-change">↑ 15% 较上周</p>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-info">
          <h3>新用户</h3>
          <p class="stat-number">23</p>
          <p class="stat-change">↑ 5% 较昨日</p>
        </div>
      </div>
    </div>

    <div class="dashboard-content">
      <div class="content-section">
        <h2>最近活动</h2>
        <div class="activity-list">
          <div v-for="activity in recentActivities" :key="activity.id" class="activity-item">
            <div class="activity-icon">{{ activity.icon }}</div>
            <div class="activity-details">
              <p class="activity-text">{{ activity.text }}</p>
              <span class="activity-time">{{ activity.time }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="content-section">
        <h2>快捷操作</h2>
        <div class="quick-actions">
          <router-link to="/products" class="quick-action">
            <span class="action-icon">🛍️</span>
            <span class="action-text">浏览商品</span>
          </router-link>
          
          <router-link to="/profile" class="quick-action">
            <span class="action-icon">👤</span>
            <span class="action-text">个人资料</span>
          </router-link>
          
          <router-link to="/orders" class="quick-action">
            <span class="action-icon">📦</span>
            <span class="action-text">我的订单</span>
          </router-link>
          
          <router-link to="/settings" class="quick-action">
            <span class="action-icon">⚙️</span>
            <span class="action-text">系统设置</span>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue';
import { useStore } from 'vuex';

export default {
  name: 'Dashboard',
  setup() {
    const store = useStore();
    
    const currentUser = computed(() => store.getters['auth/currentUser']);

    const recentActivities = ref([
      {
        id: 1,
        icon: '🛒',
        text: '用户购买了 iPhone 14',
        time: '2分钟前'
      },
      {
        id: 2,
        icon: '📦',
        text: '新订单 #ORD20240001 已确认',
        time: '5分钟前'
      },
      {
        id: 3,
        icon: '👥',
        text: '新用户注册成功',
        time: '10分钟前'
      },
      {
        id: 4,
        icon: '💰',
        text: '支付成功 ¥2999.00',
        time: '15分钟前'
      },
      {
        id: 5,
        icon: '📊',
        text: '系统数据备份完成',
        time: '30分钟前'
      }
    ]);

    return {
      currentUser,
      recentActivities
    };
  }
};
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.dashboard-header {
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  margin: 0 0 0.5rem;
  color: #333;
  font-size: 2rem;
}

.dashboard-header p {
  margin: 0;
  color: #666;
  font-size: 1.1rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.3s, box-shadow 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  font-size: 2.5rem;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
}

.stat-info h3 {
  margin: 0 0 0.5rem;
  color: #666;
  font-size: 0.875rem;
  font-weight: 500;
  text-transform: uppercase;
}

.stat-number {
  margin: 0 0 0.25rem;
  font-size: 1.75rem;
  font-weight: 700;
  color: #333;
}

.stat-change {
  margin: 0;
  font-size: 0.875rem;
  color: #27ae60;
  font-weight: 500;
}

.dashboard-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
}

.content-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.content-section h2 {
  margin: 0 0 1.5rem;
  color: #333;
  font-size: 1.25rem;
  border-bottom: 2px solid #007bff;
  padding-bottom: 0.5rem;
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
  border-radius: 6px;
  transition: background-color 0.3s;
}

.activity-item:hover {
  background: #e9ecef;
}

.activity-icon {
  font-size: 1.2rem;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 6px;
  flex-shrink: 0;
}

.activity-details {
  flex: 1;
}

.activity-text {
  margin: 0 0 0.25rem;
  color: #333;
  font-weight: 500;
}

.activity-time {
  font-size: 0.875rem;
  color: #666;
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  transition: all 0.3s;
}

.quick-action:hover {
  background: #007bff;
  color: white;
  transform: translateY(-2px);
}

.action-icon {
  font-size: 2rem;
}

.action-text {
  font-weight: 500;
  text-align: center;
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 1rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-content {
    grid-template-columns: 1fr;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>