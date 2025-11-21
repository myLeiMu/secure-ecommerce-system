<template>
  <div class="forgot-page">
    <div class="forgot-container">
      <header class="forgot-header">
        <h1>重置密码</h1>
        <p>输入账户信息，我们会发送验证码帮助您重置密码</p>
      </header>

      <form class="forgot-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="identifier">用户名/邮箱</label>
          <input
            id="identifier"
            v-model="formData.identifier"
            type="text"
            class="form-control"
            :class="{ error: errors.identifier }"
            placeholder="请输入注册时使用的用户名或邮箱"
            @input="clearError('identifier')"
          />
          <div v-if="errors.identifier" class="error-message">{{ errors.identifier }}</div>
        </div>

        <div class="form-group">
          <label for="phone">预留手机号</label>
          <input
            id="phone"
            v-model="formData.phone"
            type="tel"
            class="form-control"
            :class="{ error: errors.phone }"
            placeholder="请输入预留手机号"
            @input="clearError('phone')"
          />
          <div v-if="errors.phone" class="error-message">{{ errors.phone }}</div>
        </div>

        <div class="form-group">
          <label for="code">短信验证码</label>
          <div class="code-input">
            <input
              id="code"
              v-model="formData.code"
              type="text"
              maxlength="6"
              class="form-control"
              :class="{ error: errors.code }"
              placeholder="请输入6位验证码"
              @input="clearError('code')"
            />
            <button
              type="button"
              class="code-btn"
              :disabled="countdown > 0 || sendingCode"
              @click="sendCode"
            >
              <LoadingSpinner v-if="sendingCode" small />
              <template v-else>{{ countdown > 0 ? `${countdown}s后重发` : '获取验证码' }}</template>
            </button>
          </div>
          <div v-if="errors.code" class="error-message">{{ errors.code }}</div>
        </div>

        <div class="form-group">
          <label for="newPassword">新密码</label>
          <input
            id="newPassword"
            v-model="formData.password"
            type="password"
            class="form-control"
            :class="{ error: errors.password }"
            placeholder="请输入8-20位包含字母和数字的密码"
            @input="clearError('password')"
          />
          <div v-if="errors.password" class="error-message">{{ errors.password }}</div>
        </div>

        <div class="form-group">
          <label for="confirmPassword">确认新密码</label>
          <input
            id="confirmPassword"
            v-model="formData.confirmPassword"
            type="password"
            class="form-control"
            :class="{ error: errors.confirmPassword }"
            placeholder="请再次输入新密码"
            @input="clearError('confirmPassword')"
          />
          <div v-if="errors.confirmPassword" class="error-message">{{ errors.confirmPassword }}</div>
        </div>

        <div v-if="feedback" :class="['feedback', feedbackType]">
          {{ feedback }}
        </div>

        <button type="submit" class="submit-btn" :disabled="submitting">
          <LoadingSpinner v-if="submitting" small />
          {{ submitting ? '提交中...' : '立即重置' }}
        </button>

        <p class="back-link">
          已想起密码？<router-link to="/login">返回登录</router-link>
        </p>
      </form>
    </div>
  </div>
</template>

<script>
import { reactive, ref } from 'vue';
import LoadingSpinner from '../../components/common/LoadingSpinner.vue';
import { SecurityUtils } from '../../utils/security';
import { userAPI } from '../../services/api/userAPI';

export default {
  name: 'ForgotPassword',
  components: {
    LoadingSpinner
  },
  setup() {
    const formData = reactive({
      identifier: '',
      phone: '',
      code: '',
      password: '',
      confirmPassword: ''
    });
    const errors = reactive({});
    const submitting = ref(false);
    const sendingCode = ref(false);
    const countdown = ref(0);
    const feedback = ref('');
    const feedbackType = ref('success');

    const validate = () => {
      errors.identifier = '';
      errors.phone = '';
      errors.code = '';
      errors.password = '';
      errors.confirmPassword = '';

      if (!formData.identifier.trim()) {
        errors.identifier = '用户名或邮箱不能为空';
      }
      if (!formData.phone.trim()) {
        errors.phone = '请填写预留手机号';
      }
      if (!formData.code.trim()) {
        errors.code = '请输入验证码';
      } else if (!/^\d{6}$/.test(formData.code.trim())) {
        errors.code = '验证码必须为6位数字';
      }
      if (!formData.password.trim()) {
        errors.password = '请设置新密码';
      } else if (!SecurityUtils.validatePassword(formData.password.trim())) {
        errors.password = '密码需8-20位，包含字母和数字';
      }
      if (!formData.confirmPassword.trim()) {
        errors.confirmPassword = '请再次输入新密码';
      } else if (formData.password.trim() !== formData.confirmPassword.trim()) {
        errors.confirmPassword = '两次输入的密码不一致';
      }

      return !errors.identifier && !errors.phone && !errors.code && !errors.password && !errors.confirmPassword;
    };

    const clearError = (field) => {
      errors[field] = '';
      feedback.value = '';
    };

    const sendCode = async () => {
      if (!formData.phone.trim()) {
        errors.phone = '请先输入预留手机号';
        return;
      }
      sendingCode.value = true;
      try {
        const phone = SecurityUtils.sanitizeInput(formData.phone.trim());
        const response = await userAPI.sendResetCode({ phone });
        if (response.code !== 0) {
          throw new Error(response.message || '验证码发送失败');
        }
        feedback.value = `验证码已发送至 ${phone.slice(0, 3)}****${phone.slice(-2)}`;
        feedbackType.value = 'success';
        countdown.value = 60;
        const timer = setInterval(() => {
          countdown.value -= 1;
          if (countdown.value <= 0) {
            clearInterval(timer);
          }
        }, 1000);
      } catch (error) {
        feedback.value = error.message || '验证码发送失败，请稍后重试';
        feedbackType.value = 'error';
      } finally {
        sendingCode.value = false;
      }
    };

    const handleSubmit = async () => {
      if (!validate()) return;
      submitting.value = true;
      feedback.value = '';

      const payload = {
        phone: SecurityUtils.sanitizeInput(formData.phone.trim()),
        code: SecurityUtils.sanitizeInput(formData.code.trim()),
        new_password: formData.password.trim()
      };

      try {
        const response = await userAPI.resetPassword(payload);
        if (response.code !== 0) {
          throw new Error(response.message || '重置失败，请稍后重试');
        }
        feedback.value = '密码已重置成功，请使用新密码登录';
        feedbackType.value = 'success';
      } catch (error) {
        feedback.value = error.message || '重置失败，请稍后重试';
        feedbackType.value = 'error';
      } finally {
        submitting.value = false;
      }
    };

    return {
      formData,
      errors,
      submitting,
      sendingCode,
      countdown,
      feedback,
      feedbackType,
      handleSubmit,
      clearError,
      sendCode
    };
  }
};
</script>

<style scoped>
.forgot-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #60a5fa, #2563eb);
  padding: 1rem;
}

.forgot-container {
  width: 100%;
  max-width: 480px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(37, 99, 235, 0.2);
  overflow: hidden;
}

.forgot-header {
  padding: 2rem;
  background: #f1f5f9;
  text-align: center;
}

.forgot-header h1 {
  margin-bottom: 0.5rem;
  color: #1f2937;
}

.forgot-header p {
  margin: 0;
  color: #475569;
}

.forgot-form {
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.code-input {
  display: flex;
  gap: 0.75rem;
}

.code-input .form-control {
  flex: 1;
}

.code-btn {
  padding: 0.65rem 1rem;
  border: none;
  border-radius: 8px;
  background: #0ea5e9;
  color: white;
  font-weight: 600;
  min-width: 120px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
}

.code-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #1f2937;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  transition: border-color 0.2s;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.form-control.error {
  border-color: #ef4444;
}

.error-message {
  margin-top: 0.25rem;
  color: #ef4444;
  font-size: 0.875rem;
}

.feedback {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}

.feedback.success {
  background: #ecfdf5;
  color: #047857;
}

.feedback.error {
  background: #fef2f2;
  color: #b91c1c;
}

.submit-btn {
  width: 100%;
  padding: 0.85rem;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.submit-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.back-link {
  margin-top: 1.25rem;
  text-align: center;
  color: #475569;
}

.back-link a {
  color: #2563eb;
  font-weight: 600;
}

@media (max-width: 640px) {
  .forgot-header,
  .forgot-form {
    padding: 1.5rem;
  }
}
</style>