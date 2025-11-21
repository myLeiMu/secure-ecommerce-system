<template>
  <div :class="['spinner', { 'small': small }]">
    <div class="spinner-circle"></div>
  </div>
</template>

<script>
export default {
  name: 'LoadingSpinner',
  props: {
    small: {
      type: Boolean,
      default: false
    }
  }
};
</script>

<style scoped>
.spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
}

.spinner.small {
  width: 20px;
  height: 20px;
}

.spinner-circle {
  width: 100%;
  height: 100%;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner.small .spinner-circle {
  border-width: 2px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>