import { apiClient } from '../http';
import { SecurityUtils } from '../../utils/security';

export const productAPI = {
  async getProducts(params = {}) {
    const queryParams = {};
    
    // 构建查询参数并安全处理
    Object.keys(params).forEach(key => {
      const value = params[key];
      if (value !== null && value !== undefined && value !== '') {
        queryParams[key] = typeof value === 'string' ? SecurityUtils.sanitizeInput(value) : value;
      }
    });

    try {
      console.log('🛜 发送商品列表请求:', queryParams);
      const response = await apiClient.request('GET', '/products', null, {
        params: queryParams
      });
      console.log('🛜 商品列表响应:', response);
      return response;
    } catch (error) {
      console.error('❌ 获取商品列表失败:', error);
      throw error;
    }
  },

  async getProductDetail(productId) {
    try {
      console.log('🛜 发送商品详情请求:', productId);
      const response = await apiClient.request('GET', `/products/${productId}`);
      console.log('🛜 商品详情响应:', response);
      return response;
    } catch (error) {
      console.error('❌ 获取商品详情失败:', error);
      throw error;
    }
  },

  async searchProducts(keyword, filters = {}) {
    const params = { 
      keyword: SecurityUtils.sanitizeInput(keyword),
      ...filters 
    };
    return this.getProducts(params);
  },

  // 使用新的分类接口
  async getCategories() {
    try {
      console.log('🛜 发送分类列表请求');
      const response = await apiClient.request('GET', '/categories');
      console.log('🛜 分类列表响应:', response);
      return response;
    } catch (error) {
      console.error('❌ 获取分类失败:', error);
      // 直接抛出错误，不返回默认数据
      throw error;
    }
  }
};