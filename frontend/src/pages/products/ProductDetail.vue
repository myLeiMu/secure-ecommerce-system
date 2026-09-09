<template>
  <div class="product-detail-page">
    <div v-if="loading" class="loading-section">
      <LoadingSpinner />
      <p>加载商品详情中...</p>
    </div>

    <div v-else-if="error" class="error-section">
      <ErrorMessage :message="error" :retry="fetchProductDetail" />
    </div>

    <div v-else-if="product" class="product-detail">
      <!-- 面包屑导航 -->
      <nav class="breadcrumb">
        <router-link to="/">首页</router-link>
        <span class="separator">/</span>
        <router-link to="/products">商品列表</router-link>
        <span class="separator">/</span>
        <span class="current">{{ product.product_name }}</span>
      </nav>

      <div class="product-main">
        <!-- 商品图片 -->
        <div class="product-gallery">
          <div class="main-image">
            <img referrerpolicy="no-referrer" 
              :src="currentImage" 
              :alt="product.product_name"
              @error="handleImageError"
            />
          </div>
          <div class="image-thumbnails">
            <div
              v-for="(image, index) in product.image_urls || []"
              :key="index"
              :class="['thumbnail', { active: currentImageIndex === index }]"
              @click="currentImageIndex = index"
            >
              <img referrerpolicy="no-referrer" :src="image" :alt="`${product.product_name} ${index + 1}`" />
            </div>
          </div>
        </div>

        <!-- 商品信息 -->
        <div class="product-info">
          <h1 class="product-title">{{ product.product_name }}</h1>
          <div class="product-meta">
            <span class="sku">SKU: {{ product.sku || 'N/A' }}</span>
            <span class="category">分类: {{ product.category_name || '未分类' }}</span>
          </div>

          <div class="product-price">
            <span class="current-price">¥{{ product.sale_price }}</span>
            <span v-if="product.compare_price" class="original-price">¥{{ product.compare_price }}</span>
            <span v-if="product.compare_price" class="discount">
              {{ calculateDiscount(product.sale_price, product.compare_price) }}折
            </span>
          </div>

          <div class="product-stock">
            <span :class="['stock-status', { 'in-stock': product.stock_quantity > 0, 'out-of-stock': product.stock_quantity === 0 }]">
              {{ product.stock_quantity > 0 ? `有货 (${product.stock_quantity}件)` : '缺货' }}
            </span>
          </div>

          <div class="product-description">
            <h3>商品描述</h3>
            <p>{{ product.description || '暂无详细描述' }}</p>
          </div>

          <!-- 购买操作 -->
          <div class="purchase-section">
            <div class="quantity-selector">
              <label>数量:</label>
              <div class="quantity-controls">
                <button @click="decreaseQuantity" :disabled="quantity <= 1">-</button>
                <input v-model.number="quantity" type="number" min="1" :max="product.stock_quantity" @change="validateQuantity" />
                <button @click="increaseQuantity" :disabled="quantity >= product.stock_quantity">+</button>
              </div>
            </div>
            <p v-if="notice" class="action-notice">{{ notice }}</p>

            <div class="action-buttons">
              <button 
                @click="addToCart" 
                :disabled="product.stock_quantity === 0"
                class="add-to-cart-btn"
              >
                🛒 加入购物车
              </button>
              <button 
                @click="buyNow" 
                :disabled="product.stock_quantity === 0"
                class="buy-now-btn"
              >
                🚀 立即购买
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 商品详情 -->
      <div class="product-details-section">
        <h2>商品详情</h2>
        <div class="details-content">
          <div v-if="product.specifications" class="specifications">
            <h3>规格参数</h3>
            <div class="specs-list">
              <div v-for="(value, key) in product.specifications" :key="key" class="spec-item">
                <span class="spec-name">{{ key }}:</span>
                <span class="spec-value">{{ value }}</span>
              </div>
            </div>
          </div>
          <div v-else>
            <p>暂无详细规格信息</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { productAPI } from '../../services/api/productAPI';
import { cartAPI } from '../../services/api/cartAPI';
import LoadingSpinner from '../../components/common/LoadingSpinner.vue';
import ErrorMessage from '../../components/common/ErrorMessage.vue';
import { useStore } from 'vuex';

export default {
  name: 'ProductDetail',
  components: {
    LoadingSpinner,
    ErrorMessage
  },
  setup() {
    const store = useStore();
    const route = useRoute();
    const router = useRouter();
    
    const product = ref(null);
    const loading = ref(false);
    const error = ref('');
    const notice = ref('');
    const quantity = ref(1);
    const currentImageIndex = ref(0);

    const productId = computed(() => route.params.id);

    const currentImage = computed(() => {
      if (!product.value || !product.value.image_urls || product.value.image_urls.length === 0) {
        return '/placeholder-image.jpg';
      }
      return product.value.image_urls[currentImageIndex.value] || product.value.image_urls[0] || '/placeholder-image.jpg';
    });

    const fetchProductDetail = async () => {
      if (!productId.value) {
        error.value = '商品ID无效';
        return;
      }

      try {
        loading.value = true;
        error.value = '';

        const response = await productAPI.getProductDetail(productId.value);
        
        if (response.code === 0 && response.data) {
          product.value = response.data;
          quantity.value = 1;
          currentImageIndex.value = 0;
        } else {
          error.value = response.message || '商品不存在';
        }
      } catch (err) {
        console.error('获取商品详情错误:', err);
        error.value = err.message || '获取商品详情失败';
      } finally {
        loading.value = false;
      }
    };

    const formatPrice = (price) => {
      if (!price) return '0.00';
      return parseFloat(price).toFixed(2);
    };

    const calculateDiscount = (salePrice, comparePrice) => {
      if (!salePrice || !comparePrice || comparePrice <= salePrice) return '0';
      return ((salePrice / comparePrice) * 10).toFixed(1);
    };

    const handleImageError = (event) => {
      event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvuWDj+WbvueahOa1i+ivlTwvdGV4dD48L3N2Zz4=';
    };

    const handleThumbnailError = (event) => {
      event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2RkZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77lg488L3RleHQ+PC9zdmc+';
    };

    const validateQuantity = () => {
      if (!product.value) return;
      
      if (quantity.value < 1) {
        quantity.value = 1;
      } else if (quantity.value > product.value.stock_quantity) {
        quantity.value = product.value.stock_quantity;
      }
    };

    const decreaseQuantity = () => {
      if (quantity.value > 1) {
        quantity.value--;
      }
    };

    const increaseQuantity = () => {
      if (product.value && quantity.value < product.value.stock_quantity) {
        quantity.value++;
      }
    };

    const addToCart = () => {
      if (!product.value) return Promise.resolve();
      if (!store.getters['auth/isAuthenticated']) {
        router.push('/login');
        return Promise.resolve();
      }
      return cartAPI.addToCart({
        product_id: product.value.product_id,
        quantity: quantity.value
      }).then((response) => {
        if (response.code !== 0) {
          throw new Error(response.message || '加入购物车失败');
        }
        notice.value = '已加入购物车';
      }).catch((err) => {
        notice.value = err.message || '加入购物车失败';
      });
    };

    const buyNow = async () => {
      if (!product.value) return;
      await addToCart();
      router.push('/cart');
    };

    onMounted(() => {
      fetchProductDetail();
    });

    watch(productId, () => {
      fetchProductDetail();
    });

    return {
      product,
      loading,
      error,
      notice,
      quantity,
      currentImageIndex,
      currentImage,
      fetchProductDetail,
      formatPrice,
      calculateDiscount,
      handleImageError,
      handleThumbnailError,
      validateQuantity,
      decreaseQuantity,
      increaseQuantity,
      addToCart,
      buyNow
    };
  }
};
</script>

<style scoped>
.product-detail-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.breadcrumb {
  margin-bottom: 2rem;
  font-size: 0.875rem;
  color: #666;
}

.breadcrumb a {
  color: #007bff;
  text-decoration: none;
}

.breadcrumb a:hover {
  text-decoration: underline;
}

.separator {
  margin: 0 0.5rem;
}

.current {
  color: #333;
  font-weight: 500;
}

.product-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  margin-bottom: 3rem;
}

.product-gallery {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.main-image {
  width: 100%;
  height: 400px;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.main-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-thumbnails {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
}

.thumbnail {
  width: 80px;
  height: 80px;
  border: 2px solid transparent;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
}

.thumbnail.active {
  border-color: #007bff;
}

.thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.product-title {
  margin: 0;
  font-size: 1.75rem;
  color: #333;
  line-height: 1.3;
}

.product-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #666;
}

.product-price {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.current-price {
  font-size: 2rem;
  font-weight: 700;
  color: #e74c3c;
}

.original-price {
  font-size: 1.25rem;
  color: #999;
  text-decoration: line-through;
}

.discount {
  background: #e74c3c;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
}

.product-stock .in-stock {
  color: #27ae60;
  font-weight: 500;
}

.product-stock .out-of-stock {
  color: #e74c3c;
  font-weight: 500;
}

.product-description h3 {
  margin: 0 0 0.5rem;
  color: #333;
}

.product-description p {
  margin: 0;
  color: #666;
  line-height: 1.6;
}

.purchase-section {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
}

.action-notice {
  margin: 0.5rem 0 0.75rem;
  color: #0b63a5;
}

.quantity-selector {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.quantity-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quantity-controls button {
  width: 32px;
  height: 32px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.quantity-controls button:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
  color: #999;
}

.quantity-controls input {
  width: 60px;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 1rem;
}

.add-to-cart-btn,
.buy-now-btn {
  flex: 1;
  padding: 1rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.add-to-cart-btn {
  background: #3498db;
  color: white;
}

.add-to-cart-btn:hover:not(:disabled) {
  background: #2980b9;
}

.buy-now-btn {
  background: #e74c3c;
  color: white;
}

.buy-now-btn:hover:not(:disabled) {
  background: #c0392b;
}

.add-to-cart-btn:disabled,
.buy-now-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.product-details-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.product-details-section h2 {
  margin: 0 0 1.5rem;
  color: #333;
  border-bottom: 2px solid #007bff;
  padding-bottom: 0.5rem;
}

.specifications h3 {
  margin: 0 0 1rem;
  color: #333;
}

.specs-list {
  display: grid;
  gap: 0.75rem;
}

.spec-item {
  display: flex;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.spec-name {
  font-weight: 600;
  color: #333;
  min-width: 120px;
}

.spec-value {
  color: #666;
}

@media (max-width: 768px) {
  .product-main {
    grid-template-columns: 1fr;
    gap: 2rem;
  }

  .main-image {
    height: 300px;
  }

  .action-buttons {
    flex-direction: column;
  }

  .product-detail-page {
    padding: 1rem;
  }
}
</style>
