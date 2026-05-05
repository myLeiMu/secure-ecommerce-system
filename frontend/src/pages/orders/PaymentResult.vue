<template>
  <div class="payment-result-page">
    <section class="result-panel">
      <p class="eyebrow">Bank Payment</p>
      <h1>{{ title }}</h1>
      <p class="summary">{{ summary }}</p>

      <div v-if="result" class="result-list">
        <div>
          <span>订单号</span>
          <strong>{{ result.order_no }}</strong>
        </div>
        <div>
          <span>银行流水号</span>
          <strong>{{ result.bank_transaction_id }}</strong>
        </div>
        <div>
          <span>支付状态</span>
          <strong>{{ result.status === 'success' ? '支付成功' : '支付失败' }}</strong>
        </div>
        <div v-if="result.status !== 'success'">
          <span>失败原因</span>
          <strong>{{ result.reason || '银行未返回失败原因' }}</strong>
        </div>
      </div>

      <div class="actions">
        <router-link class="btn btn-primary" to="/orders">查看我的订单</router-link>
        <router-link class="btn btn-outline" to="/products">继续购物</router-link>
      </div>
    </section>
  </div>
</template>

<script>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { orderAPI } from '../../services/api/orderAPI';

export default {
  name: 'PaymentResultPage',
  setup() {
    const route = useRoute();
    const loading = ref(true);
    const result = ref(null);
    const error = ref('');

    const title = computed(() => {
      if (loading.value) return '正在确认支付结果';
      if (error.value) return '支付结果确认失败';
      return result.value?.status === 'success' ? '支付成功' : '支付失败';
    });

    const summary = computed(() => {
      if (loading.value) return '正在由电商后端解密银行返回的加密结果。';
      if (error.value) return error.value;
      if (result.value?.status !== 'success') {
        return result.value?.reason || '银行同步跳转已返回，支付未成功。';
      }
      return '银行同步跳转已返回，后台异步回调会继续更新订单状态。';
    });

    onMounted(async () => {
      loading.value = true;
      try {
        const payload = {
          encrypted_key: route.query.encrypted_key,
          iv: route.query.iv,
          data: route.query.data,
          transaction_id: route.query.transaction_id
        };
        const response = await orderAPI.parsePaymentResult(payload);
        if (response.code !== 0) {
          throw new Error(response.message || '支付结果解析失败');
        }
        result.value = response.data;
      } catch (err) {
        error.value = err.message || '支付结果解析失败';
      } finally {
        loading.value = false;
      }
    });

    return {
      title,
      summary,
      result,
    };
  }
};
</script>

<style scoped>
.payment-result-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 2rem 0;
}

.result-panel {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 2rem;
}

.eyebrow {
  margin: 0 0 0.5rem;
  color: #2563eb;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 2rem;
  color: #0f172a;
}

.summary {
  color: #475569;
}

.result-list {
  display: grid;
  gap: 0.75rem;
  margin: 1.5rem 0;
}

.result-list div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 0.75rem;
}

.actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
