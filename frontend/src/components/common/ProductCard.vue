<template>
  <div class="product-card">
    <div class="product-image">
      <img 
        :src="product.image_urls && product.image_urls[0] ? product.image_urls[0] : '/placeholder-image.jpg'" 
        :alt="product.product_name"
        @error="handleImageError"
      />
      <div v-if="!product.is_available" class="out-of-stock">已售罄</div>
    </div>
    
    <div class="product-info">
      <h3 class="product-name">{{ product.product_name }}</h3>
      <p class="product-description">{{ truncateDescription(product.description) }}</p>
      
      <div class="product-price">
        <span class="current-price">¥{{ product.sale_price }}</span>
        <span v-if="product.compare_price" class="original-price">¥{{ product.compare_price }}</span>
      </div>
      
      <div class="product-meta">
        <span class="stock">库存: {{ product.stock_quantity }}</span>
        <span class="sales">销量: {{ product.sales_count || 0 }}</span>
      </div>
      
      <div class="product-actions">
        <button 
          @click="addToCart" 
          :disabled="!product.is_available || product.stock_quantity === 0"
          class="add-to-cart-btn"
        >
          🛒 加入购物车
        </button>
        <button @click="viewDetails" class="view-details-btn">查看详情</button>
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router';

export default {
  name: 'ProductCard',
  props: {
    product: {
      type: Object,
      required: true
    }
  },
  setup(props, { emit }) {
    const router = useRouter();
    
    const truncateDescription = (description) => {
      if (!description) return '暂无描述';
      return description.length > 60 ? description.substring(0, 60) + '...' : description;
    };
    
    const handleImageError = (event) => {
      event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvuWDj+WbvueahOa1i+ivlTwvdGV4dD48L3N2Zz4=';
    };
    
    const addToCart = () => {
      emit('add-to-cart', props.product);
    };
    
    const viewDetails = () => {
      router.push(`/products/${props.product.product_id}`);
    };
    
    return {
      truncateDescription,
      handleImageError,
      addToCart,
      viewDetails
    };
  }
};
</script>

<style scoped>
.product-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.product-image {
  position: relative;
  width: 100%;
  height: 200px;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.product-card:hover .product-image img {
  transform: scale(1.05);
}

.out-of-stock {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: rgba(220, 53, 69, 0.9);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.product-info {
  padding: 1rem;
}

.product-name {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  line-height: 1.3;
}

.product-description {
  margin: 0 0 1rem;
  color: #666;
  font-size: 0.875rem;
  line-height: 1.4;
}

.product-price {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.current-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e74c3c;
}

.original-price {
  font-size: 0.875rem;
  color: #999;
  text-decoration: line-through;
}

.product-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #666;
  margin-bottom: 1rem;
}

.product-actions {
  display: flex;
  gap: 0.5rem;
}

.add-to-cart-btn,
.view-details-btn {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.3s;
}

.add-to-cart-btn {
  background: #3498db;
  color: white;
}

.add-to-cart-btn:hover:not(:disabled) {
  background: #2980b9;
}

.add-to-cart-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.view-details-btn {
  background: #ecf0f1;
  color: #333;
  border: 1px solid #bdc3c7;
}

.view-details-btn:hover {
  background: #d5dbdb;
}

@media (max-width: 768px) {
  .product-actions {
    flex-direction: column;
  }
}
</style>