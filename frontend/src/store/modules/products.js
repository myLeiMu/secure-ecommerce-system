const state = {
  products: [],
  currentProduct: null,
  loading: false,
  error: null,
  filters: {
    keyword: '',
    category_id: '',
    min_price: '',
    max_price: ''
  },
  pagination: {
    currentPage: 1,
    totalPages: 1,
    hasMore: true
  }
};

const mutations = {
  SET_PRODUCTS(state, products) {
    state.products = products;
  },

  ADD_PRODUCTS(state, products) {
    state.products.push(...products);
  },

  SET_CURRENT_PRODUCT(state, product) {
    state.currentProduct = product;
  },

  SET_LOADING(state, loading) {
    state.loading = loading;
  },

  SET_ERROR(state, error) {
    state.error = error;
  },

  CLEAR_ERROR(state) {
    state.error = null;
  },

  SET_FILTERS(state, filters) {
    state.filters = { ...state.filters, ...filters };
  },

  CLEAR_FILTERS(state) {
    state.filters = {
      keyword: '',
      category_id: '',
      min_price: '',
      max_price: ''
    };
  },

  SET_PAGINATION(state, pagination) {
    state.pagination = { ...state.pagination, ...pagination };
  },

  UPDATE_PRODUCT_STOCK(state, { productId, quantity }) {
    const product = state.products.find(p => p.product_id === productId);
    if (product) {
      product.stock_quantity -= quantity;
    }
    
    if (state.currentProduct && state.currentProduct.product_id === productId) {
      state.currentProduct.stock_quantity -= quantity;
    }
  }
};

const actions = {
  async fetchProducts({ commit, state }, { reset = true } = {}) {
    if (state.loading) return;

    commit('SET_LOADING', true);
    commit('CLEAR_ERROR');

    try {
      const page = reset ? 1 : state.pagination.currentPage + 1;
      
      // 这里应该调用实际的API
      // const response = await productAPI.getProducts({
      //   ...state.filters,
      //   page,
      //   limit: 12
      // });

      // 模拟数据
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const mockProducts = Array.from({ length: 12 }, (_, index) => ({
        product_id: reset ? index + 1 : state.products.length + index + 1,
        product_name: `商品 ${reset ? index + 1 : state.products.length + index + 1}`,
        description: `这是商品 ${reset ? index + 1 : state.products.length + index + 1} 的描述`,
        sale_price: Math.floor(Math.random() * 1000) + 100,
        stock_quantity: Math.floor(Math.random() * 100),
        image_urls: ['https://via.placeholder.com/300'],
        category_id: Math.floor(Math.random() * 4) + 1,
        category_name: ['电子产品', '服装', '家居', '图书'][Math.floor(Math.random() * 4)],
        is_available: true,
        created_at: new Date().toISOString()
      }));

      if (reset) {
        commit('SET_PRODUCTS', mockProducts);
        commit('SET_PAGINATION', { currentPage: 1, hasMore: true });
      } else {
        commit('ADD_PRODUCTS', mockProducts);
        commit('SET_PAGINATION', { 
          currentPage: page,
          hasMore: mockProducts.length === 12 
        });
      }
    } catch (error) {
      commit('SET_ERROR', error.message);
    } finally {
      commit('SET_LOADING', false);
    }
  },

  async fetchProductDetail({ commit }, productId) {
    commit('SET_LOADING', true);
    commit('CLEAR_ERROR');

    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const mockProduct = {
        product_id: productId,
        product_name: `商品 ${productId}`,
        description: `这是商品 ${productId} 的详细描述，包含完整的商品信息和规格参数。`,
        sale_price: 2999,
        compare_price: 3999,
        stock_quantity: 50,
        sku: `SKU${productId.toString().padStart(6, '0')}`,
        image_urls: [
          'https://via.placeholder.com/600x400',
          'https://via.placeholder.com/600x400/007bff',
          'https://via.placeholder.com/600x400/28a745'
        ],
        category_id: 1,
        category_name: '电子产品',
        specifications: {
          '品牌': '示例品牌',
          '型号': 'MODEL-X1',
          '颜色': '黑色',
          '重量': '1.2kg',
          '尺寸': '15.6 x 23.4 x 1.8 cm'
        },
        is_available: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      commit('SET_CURRENT_PRODUCT', mockProduct);
    } catch (error) {
      commit('SET_ERROR', error.message);
    } finally {
      commit('SET_LOADING', false);
    }
  },

  updateFilters({ commit }, filters) {
    commit('SET_FILTERS', filters);
  },

  clearFilters({ commit }) {
    commit('CLEAR_FILTERS');
  },

  updateProductStock({ commit }, { productId, quantity }) {
    commit('UPDATE_PRODUCT_STOCK', { productId, quantity });
  },

  clearCurrentProduct({ commit }) {
    commit('SET_CURRENT_PRODUCT', null);
  },

  clearError({ commit }) {
    commit('CLEAR_ERROR');
  }
};

const getters = {
  products: state => state.products,
  currentProduct: state => state.currentProduct,
  productsLoading: state => state.loading,
  productsError: state => state.error,
  productsFilters: state => state.filters,
  productsPagination: state => state.pagination
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
};