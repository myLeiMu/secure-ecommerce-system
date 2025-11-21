<template>
  <div v-if="message" class="error-message">
    <div class="error-icon">⚠️</div>
    <div class="error-content">
      <p class="error-text">{{ message }}</p>
      <button v-if="retry" @click="handleRetry" class="retry-btn">重试</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ErrorMessage',
  props: {
    message: {
      type: String,
      default: ''
    },
    retry: {
      type: Function,
      default: null
    }
  },
  methods: {
    handleRetry() {
      if (this.retry) {
        this.retry();
      }
    }
  }
};
</script>

<style scoped>
.error-message {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
  margin: 1rem 0;
}

.error-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.error-content {
  flex: 1;
}

.error-text {
  margin: 0 0 0.5rem;
  line-height: 1.4;
}

.retry-btn {
  padding: 0.25rem 0.75rem;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.retry-btn:hover {
  background: #c82333;
}
</style>