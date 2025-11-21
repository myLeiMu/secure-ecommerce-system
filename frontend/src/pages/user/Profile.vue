<template>
  <div class="profile-page">
    <div class="profile-header">
      <div>
        <p class="eyebrow">Account Center</p>
        <h1>个人中心</h1>
        <p>同步账户信息、修改密码并查看最近的安全事件。</p>
      </div>
      <button class="btn danger" @click="handleLogout">退出登录</button>
    </div>

    <div class="profile-grid">
      <section class="profile-card info-card">
        <div class="card-header">
          <h2>基本信息</h2>
          <button class="link-btn" @click="fetchUserProfile">刷新</button>
        </div>

        <div v-if="loading" class="loading-section">
          <LoadingSpinner />
          <p>加载中...</p>
        </div>

        <div v-else-if="currentUser" class="info-list">
          <div class="info-row">
            <label>用户ID</label>
            <span>{{ currentUser.user_id }}</span>
          </div>
          <div class="info-row">
            <label>用户名</label>
            <span>{{ currentUser.username }}</span>
          </div>
          <div class="info-row">
            <label>邮箱</label>
            <span>{{ currentUser.email || '未设置' }}</span>
          </div>
          <div class="info-row">
            <label>手机号</label>
            <span>{{ currentUser.phone || '未设置' }}</span>
          </div>
          <div class="info-row">
            <label>角色</label>
            <span class="tag info">{{ currentUser.user_role || 'normal' }}</span>
          </div>
          <div class="info-row">
            <label>状态</label>
            <span :class="['tag', currentUser.is_verified ? 'success' : 'warning']">
              {{ currentUser.is_verified ? '已验证' : '未验证' }}
            </span>
          </div>
          <div class="info-row">
            <label>注册时间</label>
            <span>{{ formatDate(currentUser.created_at) }}</span>
          </div>
          <div class="info-row">
            <label>最后登录</label>
            <span>{{ formatDate(currentUser.last_login) }}</span>
          </div>
        </div>

        <div v-else class="error-section">
          <ErrorMessage message="无法加载用户信息" :retry="fetchUserProfile" />
        </div>
      </section>

      <section class="profile-card form-card">
        <h2>编辑个人资料</h2>
        <form @submit.prevent="handleProfileUpdate" class="profile-form">
          <div class="form-group">
            <label for="profile-username">用户名</label>
            <input
              id="profile-username"
              v-model="profileForm.username"
              type="text"
              :class="['form-control', { error: profileErrors.username }]"
              placeholder="4-20位字母、数字或下划线"
            />
            <p v-if="profileErrors.username" class="form-error">{{ profileErrors.username }}</p>
          </div>

          <div class="form-group">
            <label for="profile-email">邮箱</label>
            <input
              id="profile-email"
              v-model="profileForm.email"
              type="email"
              :class="['form-control', { error: profileErrors.email }]"
              placeholder="请输入有效邮箱"
            />
            <p v-if="profileErrors.email" class="form-error">{{ profileErrors.email }}</p>
          </div>

          <div class="form-group">
            <label for="profile-phone">手机号</label>
            <input
              id="profile-phone"
              v-model="profileForm.phone"
              type="tel"
              :class="['form-control', { error: profileErrors.phone }]"
              placeholder="请输入手机号"
            />
            <p v-if="profileErrors.phone" class="form-error">{{ profileErrors.phone }}</p>
          </div>

          <div class="form-feedback">
            <p v-if="userSuccess" class="success">{{ userSuccess }}</p>
            <p v-if="userError" class="error">{{ userError }}</p>
          </div>

          <button class="btn primary" type="submit" :disabled="userLoading">
            <LoadingSpinner v-if="userLoading" small />
            保存修改
          </button>
        </form>
      </section>

      <section class="profile-card form-card">
        <h2>密码安全</h2>
        <form @submit.prevent="handlePasswordChange" class="profile-form">
          <div class="form-group">
            <label for="old-password">当前密码</label>
            <input
              id="old-password"
              type="password"
              v-model="passwordForm.oldPassword"
              :class="['form-control', { error: passwordErrors.oldPassword }]"
            />
            <p v-if="passwordErrors.oldPassword" class="form-error">{{ passwordErrors.oldPassword }}</p>
          </div>

          <div class="form-group">
            <label for="new-password">新密码</label>
            <input
              id="new-password"
              type="password"
              v-model="passwordForm.newPassword"
              :class="['form-control', { error: passwordErrors.newPassword }]"
              placeholder="至少8位，包含字母和数字"
            />
            <p v-if="passwordErrors.newPassword" class="form-error">{{ passwordErrors.newPassword }}</p>
          </div>

          <div class="form-group">
            <label for="confirm-password">确认新密码</label>
            <input
              id="confirm-password"
              type="password"
              v-model="passwordForm.confirmPassword"
              :class="['form-control', { error: passwordErrors.confirmPassword }]"
            />
            <p v-if="passwordErrors.confirmPassword" class="form-error">{{ passwordErrors.confirmPassword }}</p>
          </div>

          <div class="form-feedback">
            <p v-if="passwordFeedback" :class="['status-text', passwordFeedbackType]">
              {{ passwordFeedback }}
            </p>
          </div>

          <button class="btn secondary" type="submit" :disabled="userLoading">
            <LoadingSpinner v-if="userLoading" small />
            更新密码
          </button>
        </form>
      </section>

      <section class="profile-card security-card">
        <h2>最近安全事件</h2>
        <ul class="security-list">
          <li v-for="item in securityLogs" :key="item.id">
            <div>
              <p class="event">{{ item.event }}</p>
              <p class="device">{{ item.device }} · {{ item.ip }}</p>
            </div>
            <span class="time">{{ item.time }}</span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script>
import { reactive, ref, computed, watch, onMounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import LoadingSpinner from '../../components/common/LoadingSpinner.vue';
import ErrorMessage from '../../components/common/ErrorMessage.vue';
import { SecurityUtils } from '../../utils/security';

export default {
  name: 'ProfilePage',
  components: {
    LoadingSpinner,
    ErrorMessage
  },
  setup() {
    const store = useStore();
    const router = useRouter();

    const loading = ref(true);
    const profileForm = reactive({
      username: '',
      email: '',
      phone: ''
    });
    const profileErrors = reactive({});

    const passwordForm = reactive({
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    });
    const passwordErrors = reactive({});
    const passwordFeedback = ref('');
    const passwordFeedbackType = ref('success');

    const currentUser = computed(() => store.getters['auth/currentUser']);
    const userLoading = computed(() => store.getters['user/userLoading']);
    const userError = computed(() => store.getters['user/userError']);
    const userSuccess = computed(() => store.getters['user/userSuccess']);

    const securityLogs = ref([
      { id: 1, event: '登录成功', device: 'Chrome · Windows', ip: '192.168.0.12', time: '刚刚' },
      { id: 2, event: '密码修改', device: 'Safari · iOS', ip: '172.16.40.2', time: '2小时前' },
      { id: 3, event: 'Token 刷新', device: 'Edge · Windows', ip: '10.0.0.5', time: '昨天 16:21' }
    ]);

    const fillProfileForm = (profile) => {
      if (!profile) return;
      profileForm.username = profile.username || '';
      profileForm.email = profile.email || '';
      profileForm.phone = profile.phone || '';
    };

    watch(currentUser, (value) => {
      fillProfileForm(value);
      if (value) {
        store.dispatch('user/cacheProfile', value);
      }
    }, { immediate: true });

    const validateProfile = () => {
      profileErrors.username = '';
      profileErrors.email = '';
      profileErrors.phone = '';

      if (!profileForm.username.trim()) {
        profileErrors.username = '用户名不能为空';
      }
      if (profileForm.email && !SecurityUtils.validateEmail(profileForm.email)) {
        profileErrors.email = '邮箱格式不正确';
      }
      if (profileForm.phone && !/^1[3-9]\d{9}$/.test(profileForm.phone)) {
        profileErrors.phone = '手机号格式不正确';
      }
      return !profileErrors.username && !profileErrors.email && !profileErrors.phone;
    };

    const handleProfileUpdate = async () => {
      if (!validateProfile()) return;
      await store.dispatch('user/updateProfile', {
        username: profileForm.username,
        email: profileForm.email,
        phone: profileForm.phone
      });
    };

    const validatePassword = () => {
      passwordErrors.oldPassword = '';
      passwordErrors.newPassword = '';
      passwordErrors.confirmPassword = '';

      if (!passwordForm.oldPassword) {
        passwordErrors.oldPassword = '请输入当前密码';
      }
      if (!SecurityUtils.validatePassword(passwordForm.newPassword)) {
        passwordErrors.newPassword = '新密码需8-20位且包含字母和数字';
      }
      if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        passwordErrors.confirmPassword = '两次输入的密码不一致';
      }

      return !passwordErrors.oldPassword && !passwordErrors.newPassword && !passwordErrors.confirmPassword;
    };

    const handlePasswordChange = async () => {
      if (!validatePassword()) return;
      const result = await store.dispatch('user/changePassword', {
        oldPassword: passwordForm.oldPassword,
        newPassword: passwordForm.newPassword
      });
      passwordFeedbackType.value = result.success ? 'success' : 'error';
      passwordFeedback.value = result.success ? '密码已更新' : result.error;
      if (result.success) {
        passwordForm.oldPassword = '';
        passwordForm.newPassword = '';
        passwordForm.confirmPassword = '';
      }
    };

    const fetchUserProfile = async () => {
      loading.value = true;
      try {
        await store.dispatch('auth/fetchProfile', { silent: true });
      } finally {
        loading.value = false;
      }
    };

    const handleLogout = async () => {
      await store.dispatch('auth/logout');
      router.push('/login');
    };

    onMounted(() => {
      fetchUserProfile();
    });

    return {
      loading,
      currentUser,
      profileForm,
      profileErrors,
      passwordForm,
      passwordErrors,
      passwordFeedback,
      passwordFeedbackType,
      securityLogs,
      userLoading,
      userError,
      userSuccess,
      fetchUserProfile,
      handleProfileUpdate,
      handlePasswordChange,
      handleLogout,
      formatDate: (date) => {
        if (!date) return '未知';
        return new Date(date).toLocaleString('zh-CN');
      }
    };
  }
};
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.eyebrow {
  text-transform: uppercase;
  font-size: 0.8rem;
  letter-spacing: 0.2em;
  color: #6366f1;
  margin-bottom: 0.25rem;
}

.profile-header h1 {
  margin: 0;
  font-size: 2.1rem;
  color: #0f172a;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
}

.profile-card {
  background: white;
  border-radius: 16px;
  padding: 1.75rem;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.06);
  border: 1px solid #e5e7eb;
}

.info-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-header h2,
.profile-card h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #0f172a;
}

.link-btn {
  border: none;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 0.75rem;
}

.info-row label {
  color: #475569;
  font-weight: 600;
}

.info-row span {
  color: #0f172a;
  font-weight: 500;
}

.tag {
  padding: 0.2rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
}

.tag.success {
  background: #ecfdf5;
  color: #047857;
}

.tag.warning {
  background: #fef3c7;
  color: #b45309;
}

.tag.info {
  background: #e0f2fe;
  color: #0369a1;
}

.loading-section {
  text-align: center;
}

.form-card form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-control {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.form-control.error {
  border-color: #f87171;
}

.form-error {
  color: #dc2626;
  font-size: 0.85rem;
}

.form-feedback {
  min-height: 1rem;
}

.form-feedback .status-text {
  font-weight: 600;
}

.form-feedback .status-text.success {
  color: #059669;
}

.form-feedback .status-text.error {
  color: #dc2626;
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn.primary {
  background: #2563eb;
  color: white;
}

.btn.secondary {
  background: #0f172a;
  color: white;
}

.btn.danger {
  background: #ef4444;
  color: white;
}

.security-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.security-card li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 0.75rem;
}

.security-card .event {
  margin: 0;
  font-weight: 600;
  color: #0f172a;
}

.security-card .device {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.security-card .time {
  color: #94a3b8;
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
