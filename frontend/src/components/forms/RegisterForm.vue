<template>
  <form @submit.prevent="handleSubmit" class="register-form">
    <div class="form-group">
      <label for="username">用户名</label>
      <input
        id="username"
        v-model="formData.username"
        type="text"
        :class="['form-control', { 'error': errors.username }]"
        placeholder="3-20位字母、数字或下划线"
        @input="clearError('username')"
      />
      <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
    </div>

    <div class="form-group">
      <label for="email">邮箱</label>
      <input
        id="email"
        v-model="formData.email"
        type="email"
        :class="['form-control', { 'error': errors.email }]"
        placeholder="请输入邮箱地址"
        @input="clearError('email')"
      />
      <div v-if="errors.email" class="error-message">{{ errors.email }}</div>
    </div>

    <div class="form-group">
      <label for="phone">手机号</label>
      <input
        id="phone"
        v-model="formData.phone"
        type="tel"
        :class="['form-control', { 'error': errors.phone }]"
        placeholder="请输入手机号码"
        @input="clearError('phone')"
      />
      <div v-if="errors.phone" class="error-message">{{ errors.phone }}</div>
    </div>

    <div class="form-group">
      <label for="password">密码</label>
      <input
        id="password"
        v-model="formData.password"
        type="password"
        :class="['form-control', { 'error': errors.password }]"
        placeholder="8-20位，包含大小写字母、数字和特殊字符"
        @input="clearError('password')"
      />
      <div v-if="errors.password" class="error-message">{{ errors.password }}</div>
    </div>

    <div class="form-group">
      <label for="confirmPassword">确认密码</label>
      <input
        id="confirmPassword"
        v-model="formData.confirmPassword"
        type="password"
        :class="['form-control', { 'error': errors.confirmPassword }]"
        placeholder="请再次输入密码"
        @input="clearError('confirmPassword')"
      />
      <div v-if="errors.confirmPassword" class="error-message">{{ errors.confirmPassword }}</div>
    </div>

    <div class="form-group">
      <label for="code">验证码</label>
      <div class="code-input-group">
        <input
          id="code"
          v-model="formData.code"
          type="text"
          :class="['form-control', { 'error': errors.code }]"
          placeholder="请输入验证码"
          @input="clearError('code')"
        />
        <button 
          type="button" 
          class="code-btn"
          :disabled="codeCooldown > 0"
          @click="sendVerificationCode"
        >
          {{ codeCooldown > 0 ? `${codeCooldown}s` : '获取验证码' }}
        </button>
      </div>
      <div v-if="errors.code" class="error-message">{{ errors.code }}</div>
    </div>

    <div class="form-agreement">
      <label class="checkbox-label">
        <input type="checkbox" v-model="formData.agreed" />
        我已阅读并同意
        <a href="/agreement" target="_blank">《用户协议》</a>
        和
        <a href="/privacy" target="_blank">《隐私政策》</a>
      </label>
      <div v-if="errors.agreed" class="error-message">{{ errors.agreed }}</div>
    </div>

    <button 
      type="submit" 
      class="submit-btn"
      :disabled="loading"
    >
      <LoadingSpinner v-if="loading" small />
      {{ loading ? '注册中...' : '注册' }}
    </button>

    <ErrorMessage v-if="errors.submit" :message="errors.submit" />

    <div class="login-link">
      已有账号？<router-link to="/login">立即登录</router-link>
    </div>
  </form>
</template>

<script>
import { ref, reactive } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import { SecurityUtils } from '../../utils/security';
import { validationRules, validateForm } from '../../utils/validation';
import LoadingSpinner from '../common/LoadingSpinner.vue';
import ErrorMessage from '../common/ErrorMessage.vue';

export default {
  name: 'RegisterForm',
  components: {
    LoadingSpinner,
    ErrorMessage
  },
  setup() {
    const store = useStore();
    const router = useRouter();
    
    const formData = reactive({
      username: '',
      email: '',
      phone: '',
      password: '',
      confirmPassword: '',
      code: '',
      agreed: false
    });
    
    const errors = ref({});
    const loading = ref(false);
    const codeCooldown = ref(0);

    const registerRules = {
      username: validationRules.username,
      email: validationRules.email,
      phone: validationRules.phone,
      password: validationRules.password,
      confirmPassword: {
        required: true,
        validator: (value) => {
          if (!value) return '请确认密码';
          if (value !== formData.password) {
            return '两次输入的密码不一致';
          }
          return true;
        }
      },
      code: {
        required: true,
        validator: (value) => {
          if (!value) return '验证码不能为空';
          if (!/^\d{6}$/.test(value)) {
            return '验证码必须是6位数字';
          }
          return true;
        }
      },
      agreed: {
        required: true,
        validator: (value) => {
          if (!value) return '请同意用户协议和隐私政策';
          return true;
        }
      }
    };

    const validateRegisterForm = () => {
      // 先清理数据
      Object.keys(formData).forEach(key => {
        if (typeof formData[key] === 'string') {
          formData[key] = SecurityUtils.sanitizeInput(formData[key]);
        }
      });

      const result = validateForm(formData, registerRules);
      errors.value = result.errors;
      return result.isValid;
    };

    const clearError = (field) => {
      if (errors.value[field]) {
        delete errors.value[field];
      }
      if (errors.value.submit) {
        delete errors.value.submit;
      }
    };

    const sendVerificationCode = async () => {
      if (!formData.phone) {
        errors.value.phone = '请先输入手机号';
        return;
      }

      if (!validationRules.phone.validator(formData.phone)) {
        errors.value.phone = '请输入有效的手机号码';
        return;
      }

      // 模拟发送验证码
      codeCooldown.value = 60;
      const timer = setInterval(() => {
        codeCooldown.value--;
        if (codeCooldown.value <= 0) {
          clearInterval(timer);
        }
      }, 1000);

      console.log('发送验证码到:', formData.phone);
    };

    const handleSubmit = async () => {
      if (!validateRegisterForm()) return;
      
      loading.value = true;
      
      const userData = {
        username: formData.username,
        password: formData.password,
        phone: formData.phone,
        code: formData.code,
        email: formData.email
      };
      
      const result = await store.dispatch('auth/register', userData);
      
      if (result.success) {
        // 注册成功，跳转到登录页面
        router.push({ 
          path: '/login',
          query: { registered: 'true' }
        });
      } else {
        errors.value.submit = result.error;
      }
      
      loading.value = false;
    };

    return {
      formData,
      errors,
      loading,
      codeCooldown,
      handleSubmit,
      clearError,
      sendVerificationCode
    };
  }
};
</script>

<style scoped>
.register-form {
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

.code-input-group {
  display: flex;
  gap: 0.5rem;
}

.code-input-group .form-control {
  flex: 1;
}

.code-btn {
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  min-width: 100px;
}

.code-btn:hover:not(:disabled) {
  background: #e9ecef;
}

.code-btn:disabled {
  background: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
}

.form-agreement {
  margin-bottom: 1.5rem;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #666;
  line-height: 1.4;
}

.checkbox-label a {
  color: #007bff;
  text-decoration: none;
}

.checkbox-label a:hover {
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

.submit-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.login-link {
  text-align: center;
  margin-top: 1.5rem;
  color: #666;
}

.login-link a {
  color: #007bff;
  text-decoration: none;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>