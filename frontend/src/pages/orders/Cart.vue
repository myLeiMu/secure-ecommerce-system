<template>
  <div class="cart-page">
    <div class="page-header">
      <h1>购物车</h1>
      <router-link to="/orders" class="btn btn-outline">查看我的订单</router-link>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="loading" class="state-block">加载中...</div>
    <div v-else-if="items.length === 0" class="state-block">购物车为空</div>
    <div v-else class="cart-list">
      <div class="cart-item" v-for="item in items" :key="item.product_id">
        <div class="meta">
          <h3>{{ item.product_name }}</h3>
          <p>单价：¥{{ money(item.sale_price) }}</p>
          <p>库存：{{ item.stock_quantity }}</p>
        </div>
        <div class="actions">
          <input
            type="number"
            min="1"
            :max="item.stock_quantity"
            v-model.number="item.quantity"
            @change="updateQuantity(item)"
          />
          <button class="btn btn-danger" @click="removeItem(item.product_id)">删除</button>
        </div>
        <div class="line-total">小计：¥{{ money(item.line_total) }}</div>
      </div>
    </div>

    <div v-if="items.length > 0" class="summary">
      <div class="summary-row">
        <span>商品总额</span>
        <span>¥{{ money(subtotal) }}</span>
      </div>
      <div class="summary-row">
        <span>运费</span>
        <input type="number" min="0" step="0.01" v-model.number="shippingAmount" />
      </div>
      <div class="summary-row">
        <span>优惠</span>
        <input type="number" min="0" step="0.01" v-model.number="discountAmount" />
      </div>
      <div class="summary-row total">
        <span>应付总额</span>
        <span>¥{{ money(totalAmount) }}</span>
      </div>
      <button class="btn btn-primary" :disabled="submittingOrder" @click="createOrder">
        {{ submittingOrder ? '下单中...' : '从购物车生成订单' }}
      </button>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { cartAPI } from '../../services/api/cartAPI';
import { orderAPI } from '../../services/api/orderAPI';

export default {
  name: 'CartPage',
  setup() {
    const router = useRouter();
    const items = ref([]);
    const loading = ref(false);
    const notice = ref('');
    const shippingAmount = ref(0);
    const discountAmount = ref(0);
    const submittingOrder = ref(false);

    const subtotal = computed(() => {
      return items.value.reduce((sum, item) => sum + Number(item.line_total || 0), 0);
    });

    const totalAmount = computed(() => {
      const total = subtotal.value + Number(shippingAmount.value || 0) - Number(discountAmount.value || 0);
      return total > 0 ? total : 0;
    });

    const money = (value) => Number(value || 0).toFixed(2);

    const fetchCart = async () => {
      loading.value = true;
      notice.value = '';
      try {
        const response = await cartAPI.getCart();
        if (response.code !== 0) {
          throw new Error(response.message || '获取购物车失败');
        }
        items.value = response.data || [];
      } catch (err) {
        notice.value = err.message || '获取购物车失败';
      } finally {
        loading.value = false;
      }
    };

    const updateQuantity = async (item) => {
      try {
        const quantity = Number(item.quantity || 1);
        if (quantity < 1) {
          item.quantity = 1;
          return;
        }
        const response = await cartAPI.updateCartItem(item.product_id, { quantity });
        if (response.code !== 0) {
          throw new Error(response.message || '修改失败');
        }
        await fetchCart();
      } catch (err) {
        notice.value = err.message || '修改失败';
      }
    };

    const removeItem = async (productId) => {
      try {
        const response = await cartAPI.removeCartItem(productId);
        if (response.code !== 0) {
          throw new Error(response.message || '删除失败');
        }
        await fetchCart();
      } catch (err) {
        notice.value = err.message || '删除失败';
      }
    };

    const createOrder = async () => {
      submittingOrder.value = true;
      notice.value = '';
      try {
        const response = await orderAPI.createOrderFromCart({
          shipping_amount: Number(shippingAmount.value || 0).toFixed(2),
          discount_amount: Number(discountAmount.value || 0).toFixed(2)
        });
        if (response.code !== 0) {
          throw new Error(response.message || '下单失败');
        }
        notice.value = '下单成功，已生成订单';
        router.push('/orders');
      } catch (err) {
        notice.value = err.message || '下单失败';
      } finally {
        submittingOrder.value = false;
      }
    };

    onMounted(() => {
      fetchCart();
    });

    return {
      items,
      loading,
      notice,
      shippingAmount,
      discountAmount,
      submittingOrder,
      subtotal,
      totalAmount,
      money,
      updateQuantity,
      removeItem,
      createOrder
    };
  }
};
</script>

<style scoped>
.cart-page {
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

.cart-list {
  display: grid;
  gap: 0.75rem;
}

.cart-item {
  background: white;
  border-radius: 8px;
  padding: 1rem;
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 1rem;
  align-items: center;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.actions input {
  width: 80px;
  padding: 0.45rem 0.5rem;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.summary {
  margin-top: 1rem;
  background: white;
  border-radius: 8px;
  padding: 1rem;
  display: grid;
  gap: 0.75rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-row input {
  width: 140px;
  padding: 0.4rem 0.5rem;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.total {
  font-weight: 600;
}
</style>
