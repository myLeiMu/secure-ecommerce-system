<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-header">
        <h1>创建账户</h1>
        <p>注册新用户账户</p>
      </div>
      
      <RegisterForm />
      
      <div class="register-footer">
        <p>© 2025 电商系统. 保留所有权利.</p>
      </div>
    </div>
  </div>
</template>

<script>
import RegisterForm from '../../components/forms/RegisterForm.vue';

export default {
  name: 'RegisterPage',
  components: {
    RegisterForm
  }
};
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.register-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 450px;
  overflow: hidden;
}

.register-header {
  padding: 2rem 2rem 1rem;
  text-align: center;
  background: #f8f9fa;
}

.register-header h1 {
  margin: 0 0 0.5rem;
  color: #333;
  font-size: 1.5rem;
}

.register-header p {
  margin: 0;
  color: #666;
  font-size: 0.875rem;
}

.register-footer {
  padding: 1rem 2rem;
  text-align: center;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.register-footer p {
  margin: 0;
  color: #6c757d;
  font-size: 0.75rem;
}
</style>