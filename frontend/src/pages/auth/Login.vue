<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1>欢迎登录</h1>
        <p>请登录您的账户</p>
      </div>
      
      <LoginForm />
      
      <div class="login-footer">
        <p>© 2025 电商系统. 保留所有权利.</p>
      </div>
    </div>
  </div>
</template>

<script>
import LoginForm from '../../components/forms/LoginForm.vue';

export default {
  name: 'LoginPage',
  components: {
    LoginForm
  }
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.login-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 450px;
  overflow: hidden;
}

.login-header {
  padding: 2rem 2rem 1rem;
  text-align: center;
  background: #f8f9fa;
}

.login-header h1 {
  margin: 0 0 0.5rem;
  color: #333;
  font-size: 1.5rem;
}

.login-header p {
  margin: 0;
  color: #666;
  font-size: 0.875rem;
}

.login-footer {
  padding: 1rem 2rem;
  text-align: center;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.login-footer p {
  margin: 0;
  color: #6c757d;
  font-size: 0.75rem;
}
</style>