<template>
  <div class="orders-page">
    <div class="page-header">
      <h1>我的订单</h1>
      <router-link to="/cart" class="btn btn-outline">返回购物车</router-link>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>
    <div v-if="loading" class="state-block">加载中...</div>
    <div v-else-if="orders.length === 0" class="state-block">暂无订单</div>
    <div v-else class="order-list">
      <div class="order-card" v-for="order in orders" :key="order.order_id">
        <div class="order-header">
          <div>
            <div>订单号：{{ order.order_number }}</div>
            <div>状态：{{ order.order_status }}</div>
            <div>支付状态：{{ paymentStatusText(order.payment_status) }}</div>
          </div>
          <div class="amount">¥{{ money(order.total_amount) }}</div>
        </div>
        <ul class="items">
          <li v-for="item in order.items" :key="`${order.order_id}-${item.product_id}`">
            {{ item.product_name }} × {{ item.quantity }}（¥{{ money(item.total_price) }}）
          </li>
        </ul>
        <div class="actions">
          <button
            v-if="canPay(order)"
            class="btn btn-primary"
            @click="goPay(order.order_id)"
            :disabled="payingId === order.order_id"
          >
            {{ payingId === order.order_id ? '跳转中...' : '去支付' }}
          </button>
          <button
            class="btn btn-danger"
            @click="cancelOrder(order.order_id)"
            :disabled="order.order_status === 'cancelled' || cancellingId === order.order_id"
          >
            {{ cancellingId === order.order_id ? '取消中...' : '取消订单' }}
          </button>
          <button
            v-if="order.order_status === 'cancelled'"
            class="btn btn-danger"
            @click="deleteOrder(order.order_id)"
            :disabled="deletingId === order.order_id"
          >
            {{ deletingId === order.order_id ? '删除中...' : '删除订单' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { onMounted, ref } from 'vue';
import { orderAPI } from '../../services/api/orderAPI';

export default {
  name: 'OrderListPage',
  setup() {
    const orders = ref([]);
    const loading = ref(false);
    const notice = ref('');
    const cancellingId = ref(null);
    const payingId = ref(null);
    const deletingId = ref(null);

    const money = (value) => Number(value || 0).toFixed(2);
    const paymentStatusText = (status) => ({
      pending: '待支付',
      paid: '已支付',
      failed: '支付失败',
      refunded: '已退款'
    }[status] || status || '未知');

    const canPay = (order) => (
      order.payment_status !== 'paid'
      && !['cancelled', 'refunded'].includes(order.order_status)
    );

    const fetchOrders = async () => {
      loading.value = true;
      notice.value = '';
      try {
        const response = await orderAPI.getMyOrders();
        if (response.code !== 0) {
          throw new Error(response.message || '获取订单失败');
        }
        orders.value = response.data || [];
      } catch (err) {
        notice.value = err.message || '获取订单失败';
      } finally {
        loading.value = false;
      }
    };

    const cancelOrder = async (orderId) => {
      cancellingId.value = orderId;
      notice.value = '';
      try {
        const response = await orderAPI.cancelOrder(orderId);
        if (response.code !== 0) {
          throw new Error(response.message || '取消失败');
        }
        notice.value = '订单已取消';
        await fetchOrders();
      } catch (err) {
        notice.value = err.message || '取消失败';
      } finally {
        cancellingId.value = null;
      }
    };

    const deleteOrder = async (orderId) => {
      deletingId.value = orderId;
      notice.value = '';
      try {
        const response = await orderAPI.deleteOrder(orderId);
        if (response.code !== 0) {
          throw new Error(response.message || '删除失败');
        }
        notice.value = '订单已删除';
        orders.value = orders.value.filter((order) => order.order_id !== orderId);
      } catch (err) {
        notice.value = err.message || '删除失败';
      } finally {
        deletingId.value = null;
      }
    };

    const goPay = async (orderId) => {
      payingId.value = orderId;
      notice.value = '';
      try {
        const response = await orderAPI.startBankPay(orderId);
        if (response.code !== 0) {
          throw new Error(response.message || '发起支付失败');
        }
        window.location.href = response.data.pay_url;
      } catch (err) {
        notice.value = err.message || '发起支付失败';
      } finally {
        payingId.value = null;
      }
    };

    onMounted(() => {
      fetchOrders();
    });

    return {
      orders,
      loading,
      notice,
      cancellingId,
      payingId,
      deletingId,
      money,
      paymentStatusText,
      canPay,
      cancelOrder,
      deleteOrder,
      goPay
    };
  }
};
</script>

<style scoped>
.orders-page {
  max-width: 980px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.notice {
  margin-bottom: 1rem;
  color: #0b63a5;
}

.state-block {
  background: white;
  border-radius: 8px;
  padding: 1.2rem;
  color: #666;
}

.order-list {
  display: grid;
  gap: 0.75rem;
}

.order-card {
  background: white;
  border-radius: 8px;
  padding: 1rem;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.amount {
  font-size: 1.1rem;
  font-weight: 600;
}

.items {
  margin: 0;
  padding-left: 1.1rem;
  color: #444;
}

.actions {
  margin-top: 0.75rem;
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
