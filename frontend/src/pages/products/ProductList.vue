<template>
  <div class="product-list-page">
    <div class="page-header">
      <h1>商品列表</h1>
      <p>发现心仪的商品</p>
    </div>

    <div class="filters-section">
      <div class="search-box">
        <input
          v-model="filters.keyword"
          type="text"
          placeholder="搜索商品..."
          @keyup.enter="searchProducts"
        />
        <button @click="searchProducts" class="search-btn">搜索</button>
        <button @click="clearFilters" class="clear-btn">清除</button>
      </div>

      <div class="filter-options">
        <select v-model="filters.category_id" @change="searchProducts">
          <option value="">所有分类</option>
          <option v-for="category in categories" :key="category.category_id" :value="category.category_id">
            {{ category.category_name }}
          </option>
        </select>

        <div class="price-range">
          <input
            v-model.number="filters.min_price"
            type="number"
            placeholder="最低价"
            min="0"
            @change="searchProducts"
          />
          <span>-</span>
          <input
            v-model.number="filters.max_price"
            type="number"
            placeholder="最高价"
            min="0"
            @change="searchProducts"
          />
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-section">
      <LoadingSpinner />
      <p>加载商品中...</p>
    </div>

    <div v-else-if="error" class="error-section">
      <ErrorMessage :message="error" :retry="fetchProducts" />
    </div>

    <div v-else-if="products.length === 0" class="empty-section">
      <p>暂无商品</p>
    </div>

    <div v-else class="products-grid">
      <ProductCard
        v-for="product in products"
        :key="product.product_id"
        :product="product"
        @add-to-cart="handleAddToCart"
      />
    </div>

    <div v-if="products.length > 0 && hasMore" class="pagination">
      <button 
        @click="loadMore" 
        :disabled="loading"
        class="load-more-btn"
      >
        {{ loading ? '加载中...' : '加载更多' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { productAPI } from '../../services/api/productAPI';
import { SecurityUtils } from '../../utils/security';
import ProductCard from '../../components/common/ProductCard.vue';
import LoadingSpinner from '../../components/common/LoadingSpinner.vue';
import ErrorMessage from '../../components/common/ErrorMessage.vue';

export default {
  name: 'ProductList',
  components: {
    ProductCard,
    LoadingSpinner,
    ErrorMessage
  },
  setup() {
    const route = useRoute();
    const router = useRouter();

    const products = ref([]);
    const categories = ref([]);
    const loading = ref(false);
    const error = ref('');
    const hasMore = ref(true);
    const currentPage = ref(1);

    const filters = reactive({
      keyword: '',
      category_id: '',
      min_price: '',
      max_price: ''
    });

    const buildSafeFilters = () => {
      const payload = {};
      if (filters.keyword) payload.keyword = SecurityUtils.sanitizeInput(filters.keyword);
      if (filters.category_id) payload.category_id = filters.category_id;
      if (filters.min_price) payload.min_price = filters.min_price;
      if (filters.max_price) payload.max_price = filters.max_price;
      payload.page = currentPage.value;
      payload.limit = 12;
      return payload;
    };

    const syncQueryToFilters = () => {
      const { keyword, category_id, min_price, max_price } = route.query;
      filters.keyword = keyword ? SecurityUtils.sanitizeInput(String(keyword)) : '';
      filters.category_id = category_id ? String(category_id) : '';
      filters.min_price = min_price ? String(min_price) : '';
      filters.max_price = max_price ? String(max_price) : '';
    };

    const fetchProducts = async (reset = false) => {
      if (loading.value) return;

      try {
        loading.value = true;
        error.value = '';

        if (reset) {
          products.value = [];
          currentPage.value = 1;
          hasMore.value = true;
        }

        console.log('请求商品列表参数:', buildSafeFilters());
        const response = await productAPI.getProducts(buildSafeFilters());
        console.log('商品列表API响应:', response);

        if (response.code === 0) {
          const newProducts = response.data || [];
          console.log('商品数据:', newProducts);
          
          if (reset) {
            products.value = newProducts;
          } else {
            products.value.push(...newProducts);
          }

          hasMore.value = newProducts.length === 12;
        } else {
          error.value = response.message || '获取商品列表失败';
        }
      } catch (err) {
        console.error('获取商品列表错误:', err);
        error.value = err.message || '网络错误，请重试';
      } finally {
        loading.value = false;
      }
    };

    const updateQueryFromFilters = () => {
      const query = {};
      if (filters.keyword) query.keyword = filters.keyword;
      if (filters.category_id) query.category_id = filters.category_id;
      if (filters.min_price) query.min_price = filters.min_price;
      if (filters.max_price) query.max_price = filters.max_price;

      router.replace({
        path: route.path,
        query
      });
    };

    const searchProducts = () => {
      currentPage.value = 1;
      updateQueryFromFilters();
      fetchProducts(true);
    };

    const clearFilters = () => {
      filters.keyword = '';
      filters.category_id = '';
      filters.min_price = '';
      filters.max_price = '';
      currentPage.value = 1;
      router.replace({ path: route.path });
      fetchProducts(true);
    };

    const loadMore = () => {
      if (hasMore.value && !loading.value) {
        currentPage.value++;
        fetchProducts(false);
      }
    };

    const handleAddToCart = (product) => {
      console.log('添加到购物车:', product);
    };

    const fetchCategories = async () => {
      try {
        console.log('开始获取分类数据...');
        const response = await productAPI.getCategories();
        console.log('分类API响应:', response);

        if (response.code === 0 && response.data) {
          console.log('原始分类数据:', response.data);
          categories.value = flattenCategories(response.data);
          console.log('处理后的分类数据:', categories.value);
        } else {
          console.warn('分类API返回失败:', response.message);
          categories.value = []; // 不设置默认数据
        }
      } catch (err) {
        console.error('获取分类失败:', err);
        categories.value = []; // 不设置默认数据
      }
    };

    const flattenCategories = (categoryTree) => {
      const flattened = [];
      
      const traverse = (categories) => {
        categories.forEach(category => {
          flattened.push({
            category_id: category.category_id,
            category_name: category.category_name
          });
          
          if (category.children && category.children.length > 0) {
            traverse(category.children);
          }
        });
      };
      
      traverse(categoryTree);
      return flattened;
    };

    onMounted(() => {
      console.log('ProductList 组件挂载');
      fetchCategories();
      syncQueryToFilters();
      fetchProducts(true);
    });

    watch(() => route.query, () => {
      console.log('路由查询参数变化:', route.query);
      syncQueryToFilters();
      fetchProducts(true);
    });

    return {
      products,
      categories,
      loading,
      error,
      hasMore,
      filters,
      fetchProducts,
      searchProducts,
      clearFilters,
      loadMore,
      handleAddToCart
    };
  }
};
</script>

<style scoped>
.product-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  margin: 0 0 0.5rem;
  color: #333;
  font-size: 2rem;
}

.page-header p {
  margin: 0;
  color: #666;
  font-size: 1rem;
}

.filters-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.search-box {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.search-box input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.search-box input:focus {
  outline: none;
  border-color: #007bff;
}

.search-btn {
  padding: 0.75rem 1.5rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.search-btn:hover {
  background: #0056b3;
}

.clear-btn {
  padding: 0.75rem 1rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.clear-btn:hover {
  background: #545b62;
}

.filter-options {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.filter-options select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.price-range {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.price-range input {
  width: 100px;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.loading-section,
.empty-section {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.error-section {
  margin: 2rem 0;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.pagination {
  text-align: center;
}

.load-more-btn {
  padding: 0.75rem 2rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.load-more-btn:hover:not(:disabled) {
  background: #0056b3;
}

.load-more-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .product-list-page {
    padding: 1rem;
  }

  .filter-options {
    flex-direction: column;
    align-items: stretch;
  }

  .price-range {
    justify-content: space-between;
  }

  .price-range input {
    flex: 1;
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
  }
}
</style>