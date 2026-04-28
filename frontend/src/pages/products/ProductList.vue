<template>
  <div class="product-list-page">
    <div class="page-header">
      <div>
        <h1>商品列表</h1>
        <p>支持发布、编辑、删除、加入购物车</p>
      </div>
      <button v-if="isAuthenticated" class="btn btn-primary" @click="openCreateForm">发布商品</button>
    </div>

    <div class="filters-section">
      <div class="search-box">
        <input v-model="filters.keyword" type="text" placeholder="搜索商品..." @keyup.enter="searchProducts" />
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
        <label v-if="isAuthenticated" class="mine-filter">
          <input v-model="showMineOnly" type="checkbox" />
          只看我发布的商品
        </label>
      </div>
    </div>

    <div v-if="notice" class="notice">{{ notice }}</div>
    <div v-if="formVisible" class="form-card">
      <h3>{{ editingProductId ? '编辑商品' : '发布商品' }}</h3>
      <p class="form-meta">带 <span class="required">*</span> 为必填，括号内为后端参数名</p>
      <div class="form-grid">
        <div class="form-field">
          <label class="field-label">SKU<span class="required">*</span></label>
          <input v-model="form.sku" type="text" placeholder="例如：SECOND-IP13-9A2F" :disabled="!!editingProductId" />
          <p class="field-hint">发布时必填且唯一，编辑时不可修改</p>
        </div>
        <div class="form-field">
          <label class="field-label">商品名称<span class="required">*</span></label>
          <input v-model="form.product_name" type="text" placeholder="例如：iPhone 13 128G 95新" />
          <p class="field-hint">建议写品牌 + 型号 + 成色</p>
        </div>
        <div class="form-field">
          <label class="field-label">售价<span class="required">*</span></label>
          <input v-model.number="form.sale_price" type="number" min="0" step="0.01" placeholder="例如：2899.00" />
          <p class="field-hint">单位元，最多两位小数</p>
        </div>
        <div class="form-field">
          <label class="field-label">库存<span class="required">*</span></label>
          <input v-model.number="form.stock_quantity" type="number" min="1" placeholder="二手商品通常填 1" />
          <p class="field-hint">必须大于 0</p>
        </div>
        <div class="form-field">
          <label class="field-label">分类<span class="required">*</span></label>
          <select v-model.number="form.category_id">
            <option value="">选择分类</option>
            <option v-for="category in categories" :key="category.category_id" :value="category.category_id">
              {{ category.category_name }}
            </option>
          </select>
          <p class="field-hint">请选择最匹配的交易分类</p>
        </div>
        <div class="form-field">
          <label class="field-label">图片 URL</label>
          <input v-model="form.image_urls_text" type="text" placeholder="多个链接用英文逗号分隔" />
          <p class="field-hint">示例：https://a.com/1.jpg,https://a.com/2.jpg</p>
        </div>
      </div>
      <div class="form-field">
        <label class="field-label">商品描述</label>
        <textarea v-model="form.description" rows="3" placeholder="写明成色、瑕疵、配件、交易方式等"></textarea>
      </div>
      <div class="form-actions">
        <button class="btn btn-secondary" @click="closeForm">取消</button>
        <button class="btn btn-primary" :disabled="submitting" @click="submitProduct">
          {{ submitting ? '提交中...' : '确认提交' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-section">
      <LoadingSpinner />
      <p>加载商品中...</p>
    </div>
    <div v-else-if="error" class="error-section">
      <ErrorMessage :message="error" :retry="() => fetchProducts()" />
    </div>
    <div v-else-if="displayedProducts.length === 0" class="empty-section">
      <p>暂无商品</p>
    </div>
    <div v-else class="products-grid">
      <div v-for="product in displayedProducts" :key="product.product_id" class="product-card-wrapper">
        <ProductCard :product="product" @add-to-cart="handleAddToCart" />
        <div v-if="canManage(product)" class="manage-actions">
          <button class="btn btn-outline" @click="openEditForm(product)">编辑</button>
          <button class="btn btn-danger" @click="removeProduct(product.product_id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useStore } from 'vuex';
import { useRoute, useRouter } from 'vue-router';
import ProductCard from '../../components/common/ProductCard.vue';
import LoadingSpinner from '../../components/common/LoadingSpinner.vue';
import ErrorMessage from '../../components/common/ErrorMessage.vue';
import { productAPI } from '../../services/api/productAPI';
import { cartAPI } from '../../services/api/cartAPI';

export default {
  name: 'ProductList',
  components: { ProductCard, LoadingSpinner, ErrorMessage },
  setup() {
    const store = useStore();
    const route = useRoute();
    const router = useRouter();
    const products = ref([]);
    const categories = ref([]);
    const loading = ref(false);
    const submitting = ref(false);
    const error = ref('');
    const notice = ref('');
    const showMineOnly = ref(false);
    const formVisible = ref(false);
    const editingProductId = ref(null);

    const filters = reactive({
      keyword: '',
      category_id: ''
    });

    const form = reactive({
      sku: '',
      product_name: '',
      description: '',
      sale_price: 0,
      stock_quantity: 0,
      category_id: '',
      image_urls_text: ''
    });

    const isAuthenticated = computed(() => store.getters['auth/isAuthenticated']);
    const currentUser = computed(() => store.getters['auth/currentUser'] || {});
    const isAdmin = computed(() => ['admin', 'ADMIN'].includes(currentUser.value?.user_role) || currentUser.value?.role === 'admin');
    const displayedProducts = computed(() => {
      if (!showMineOnly.value) return products.value;
      const uid = Number(currentUser.value?.user_id);
      if (!uid) return products.value;
      return products.value.filter((product) => Number(product?.seller_id) === uid);
    });

    const flattenCategories = (categoryTree) => {
      const flattened = [];
      const walk = (items) => {
        items.forEach((item) => {
          flattened.push({ category_id: item.category_id, category_name: item.category_name });
          if (Array.isArray(item.children) && item.children.length > 0) {
            walk(item.children);
          }
        });
      };
      walk(categoryTree || []);
      return flattened;
    };

    const fetchCategories = async () => {
      try {
        const response = await productAPI.getCategories();
        if (response.code === 0) {
          categories.value = flattenCategories(response.data);
        }
      } catch (err) {
        console.warn('获取分类失败:', err.message);
      }
    };

    const buildQuery = () => {
      const params = {};
      if (filters.keyword) params.keyword = filters.keyword.trim();
      if (filters.category_id) params.category_id = Number(filters.category_id);
      return params;
    };

    const fetchProducts = async () => {
      loading.value = true;
      error.value = '';
      try {
        const response = await productAPI.getProducts(buildQuery());
        if (response.code !== 0) {
          throw new Error(response.message || '获取商品失败');
        }
        products.value = response.data || [];
      } catch (err) {
        error.value = err.message || '获取商品失败';
      } finally {
        loading.value = false;
      }
    };

    const searchProducts = async () => {
      await fetchProducts();
    };

    const clearFilters = async () => {
      filters.keyword = '';
      filters.category_id = '';
      await fetchProducts();
    };

    const resetForm = () => {
      form.sku = '';
      form.product_name = '';
      form.description = '';
      form.sale_price = 0;
      form.stock_quantity = 1;
      form.category_id = '';
      form.image_urls_text = '';
      editingProductId.value = null;
    };

    const openCreateForm = () => {
      resetForm();
      formVisible.value = true;
    };

    const openEditForm = (product) => {
      editingProductId.value = product.product_id;
      form.sku = product.sku || '';
      form.product_name = product.product_name || '';
      form.description = product.description || '';
      form.sale_price = Number(product.sale_price || 0);
      form.stock_quantity = Number(product.stock_quantity || 0);
      form.category_id = Number(product.category_id || '');
      form.image_urls_text = Array.isArray(product.image_urls) ? product.image_urls.join(',') : '';
      formVisible.value = true;
    };

    const closeForm = () => {
      formVisible.value = false;
      resetForm();
    };

    const buildProductPayload = () => {
      const imageUrls = form.image_urls_text
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
      const basePayload = {
        product_name: form.product_name.trim(),
        description: form.description.trim(),
        sale_price: Number(form.sale_price || 0).toFixed(2),
        stock_quantity: Number(form.stock_quantity || 0),
        category_id: Number(form.category_id),
        image_urls: imageUrls,
        specifications: {}
      };
      if (!editingProductId.value) {
        basePayload.sku = form.sku.trim();
      }
      return basePayload;
    };

    const submitProduct = async () => {
      if (!form.product_name || !form.category_id) {
        notice.value = '请补全商品名称和分类';
        return;
      }
      if (Number(form.stock_quantity) <= 0) {
        notice.value = '库存必须大于0';
        return;
      }
      submitting.value = true;
      try {
        const payload = buildProductPayload();
        const response = editingProductId.value
          ? await productAPI.updateProduct(editingProductId.value, payload)
          : await productAPI.createProduct(payload);
        if (response.code !== 0) {
          throw new Error(response.message || '提交失败');
        }
        notice.value = editingProductId.value ? '商品已更新' : '商品已发布';
        closeForm();
        await fetchProducts();
      } catch (err) {
        notice.value = err.message || '提交失败';
      } finally {
        submitting.value = false;
      }
    };

    const canManage = (product) => {
      if (!isAuthenticated.value || !currentUser.value?.user_id) return false;
      return isAdmin.value || Number(product.seller_id) === Number(currentUser.value.user_id);
    };

    const removeProduct = async (productId) => {
      if (!window.confirm('确认删除该商品吗？')) return;
      try {
        const response = await productAPI.deleteProduct(productId);
        if (response.code !== 0) {
          throw new Error(response.message || '删除失败');
        }
        notice.value = '商品已删除';
        await fetchProducts();
      } catch (err) {
        notice.value = err.message || '删除失败';
      }
    };

    const handleAddToCart = async (product) => {
      if (!isAuthenticated.value) {
        router.push('/login');
        return;
      }
      try {
        const response = await cartAPI.addToCart({ product_id: product.product_id, quantity: 1 });
        if (response.code !== 0) {
          throw new Error(response.message || '加入购物车失败');
        }
        notice.value = '已加入购物车';
      } catch (err) {
        notice.value = err.message || '加入购物车失败';
      }
    };

    onMounted(async () => {
      if (route.query.keyword) {
        filters.keyword = String(route.query.keyword);
      }
      if (route.query.category_id) {
        filters.category_id = String(route.query.category_id);
      }
      await fetchCategories();
      await fetchProducts();
    });

    watch(() => route.query, (query) => {
      filters.keyword = query.keyword ? String(query.keyword) : '';
      filters.category_id = query.category_id ? String(query.category_id) : '';
      fetchProducts();
    });

    return {
      products,
      categories,
      filters,
      loading,
      submitting,
      error,
      notice,
      showMineOnly,
      displayedProducts,
      formVisible,
      editingProductId,
      form,
      isAuthenticated,
      searchProducts,
      clearFilters,
      openCreateForm,
      openEditForm,
      closeForm,
      submitProduct,
      canManage,
      removeProduct,
      handleAddToCart,
      fetchProducts
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
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  gap: 0.75rem;
  align-items: center;
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

.loading-section, .empty-section {
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

.product-card-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.manage-actions {
  display: flex;
  gap: 0.5rem;
}

.notice {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  background: #e8f5ff;
  color: #0b63a5;
}

.form-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 1rem;
  margin-bottom: 1rem;
}

.form-meta {
  margin: 0 0 0.8rem;
  font-size: 0.9rem;
  color: #6a6a6a;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field-label {
  font-size: 0.9rem;
  color: #333;
  font-weight: 600;
}

.field-hint {
  margin: 0;
  font-size: 0.82rem;
  color: #7a7a7a;
}

.required {
  color: #d93c3c;
}

.form-card input,
.form-card select,
.form-card textarea {
  width: 100%;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 0.6rem 0.7rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

@media (max-width: 768px) {
  .product-list-page {
    padding: 1rem;
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
