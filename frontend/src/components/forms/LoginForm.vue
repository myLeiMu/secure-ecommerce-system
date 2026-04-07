<template>
  <form @submit.prevent="handleSubmit" class="login-form">
    <div class="form-group">
      <label for="username">用户名/邮箱</label>
      <input
        id="username"
        v-model="formData.username"
        type="text"
        :class="['form-control', { 'error': errors.username }]"
        placeholder="请输入用户名或邮箱"
        @input="clearError('username')"
      />
      <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
    </div>

    <div class="form-group">
      <label for="password">密码</label>
      <input
        id="password"
        v-model="formData.password"
        type="password"
        :class="['form-control', { 'error': errors.password }]"
        placeholder="请输入密码"
        @input="clearError('password')"
      />
      <div v-if="errors.password" class="error-message">{{ errors.password }}</div>
    </div>

    <div class="form-options">
      <label class="checkbox-label">
        <input type="checkbox" v-model="formData.rememberMe" />
        记住登录状态
      </label>
      <router-link to="/forgot-password" class="forgot-link">忘记密码？</router-link>
    </div>

    <div class="form-group">
      <label for="certificateFile">证书文件（PEM/CRT/CER）</label>
      <input
        id="certificateFile"
        type="file"
        accept=".pem,.crt,.cer,text/plain"
        class="form-control"
        @change="handleCertFileChange"
      />
      <div v-if="errors.certificate" class="error-message">{{ errors.certificate }}</div>
    </div>

    <button 
      type="submit" 
      class="submit-btn"
      :disabled="loading"
    >
      <LoadingSpinner v-if="loading" small />
      {{ loading ? '登录中...' : '登录' }}
    </button>
    <button
      type="button"
      class="cert-login-btn"
      :disabled="loading"
      @click="handleCertLogin"
    >
      <LoadingSpinner v-if="loading" small />
      {{ loading ? '证书验证中...' : '浏览器证书登录' }}
    </button>
    <button
      type="button"
      class="cert-file-login-btn"
      :disabled="loading"
      @click="handleCertFileLogin"
    >
      <LoadingSpinner v-if="loading" small />
      {{ loading ? '证书验证中...' : '证书文件登录' }}
    </button>

    <ErrorMessage v-if="errors.submit" :message="errors.submit" />

    <div class="register-link">
      还没有账号？<router-link to="/register">立即注册</router-link>
    </div>
  </form>
</template>

<script>
import { ref, reactive } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import { SecurityUtils } from '../../utils/security';
import LoadingSpinner from '../common/LoadingSpinner.vue';
import ErrorMessage from '../common/ErrorMessage.vue';

export default {
  name: 'LoginForm',
  components: {
    LoadingSpinner,
    ErrorMessage
  },
  setup() {
    const store = useStore();
    const router = useRouter();
    
    const formData = reactive({
      username: '',
      password: '',
      rememberMe: false
    });
    
    const errors = ref({});
    const loading = ref(false);
    const certFile = ref(null);

    const validateForm = () => {
      const newErrors = {};
      
      if (!formData.username.trim()) {
        newErrors.username = '请输入用户名或邮箱';
      } else {
        formData.username = SecurityUtils.sanitizeInput(formData.username);
      }
      
      if (!formData.password) {
        newErrors.password = '请输入密码';
      }
      
      errors.value = newErrors;
      return Object.keys(newErrors).length === 0;
    };

    const clearError = (field) => {
      if (errors.value[field]) {
        delete errors.value[field];
      }
      if (errors.value.submit) {
        delete errors.value.submit;
      }
    };

    const handleCertFileChange = (event) => {
      certFile.value = event?.target?.files?.[0] || null;
      if (errors.value.certificate) {
        delete errors.value.certificate;
      }
      if (errors.value.submit) {
        delete errors.value.submit;
      }
    };

    const readFileAsText = (file) => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onerror = () => reject(new Error('证书文件读取失败'));
        reader.readAsText(file, 'utf-8');
      });
    };

    const handleSubmit = async () => {
      if (!validateForm()) return;
      
      loading.value = true;
      
      const credentials = {
        username: formData.username,
        password: formData.password
      };
      
      const result = await store.dispatch('auth/login', credentials);
      
      if (result.success) {
        // 登录成功，跳转到首页或原计划页面
        const redirect = router.currentRoute.value.query.redirect || '/';
        router.push(redirect);
      } else {
        errors.value.submit = result.error;
      }
      
      loading.value = false;
    };

    const handleCertLogin = async () => {
      if (!formData.username.trim()) {
        errors.value.username = '请输入用户名';
        return;
      }
      loading.value = true;
      clearError('submit');
      const username = SecurityUtils.sanitizeInput(formData.username);
      const result = await store.dispatch('auth/certMtlsLogin', username);
      if (result.success) {
        const redirect = router.currentRoute.value.query.redirect || '/';
        router.push(redirect);
      } else {
        errors.value.submit = result.error;
      }
      loading.value = false;
    };

    const handleCertFileLogin = async () => {
      if (!formData.username.trim()) {
        errors.value.username = '请输入用户名';
        return;
      }
      if (!certFile.value) {
        errors.value.certificate = '请选择证书文件';
        return;
      }
      loading.value = true;
      clearError('submit');
      try {
        const certificatePem = await readFileAsText(certFile.value);
        const username = SecurityUtils.sanitizeInput(formData.username);
        const result = await store.dispatch('auth/certFileLogin', {
          username,
          certificate_pem: certificatePem
        });
        if (result.success) {
          const redirect = router.currentRoute.value.query.redirect || '/';
          router.push(redirect);
        } else {
          errors.value.submit = result.error;
        }
      } catch (error) {
        errors.value.submit = error.message;
      } finally {
        loading.value = false;
      }
    };

    return {
      formData,
      errors,
      loading,
      certFile,
      handleSubmit,
      handleCertLogin,
      handleCertFileLogin,
      handleCertFileChange,
      clearError
    };
  }
};
</script>

<style scoped>
.login-form {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
}

.form-control.error {
  border-color: #dc3545;
}

.error-message {
  color: #dc3545;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #666;
}

.forgot-link {
  font-size: 0.875rem;
  color: #007bff;
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.submit-btn {
  width: 100%;
  padding: 0.75rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  background: #0056b3;
}

.cert-login-btn {
  width: 100%;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: #14532d;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
}

.cert-login-btn:hover:not(:disabled) {
  background: #166534;
}

.cert-file-login-btn {
  width: 100%;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: #1d4ed8;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
}

.cert-file-login-btn:hover:not(:disabled) {
  background: #1e40af;
}

.submit-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.cert-login-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.cert-file-login-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.register-link {
  text-align: center;
  margin-top: 1.5rem;
  color: #666;
}

.register-link a {
  color: #007bff;
  text-decoration: none;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>
