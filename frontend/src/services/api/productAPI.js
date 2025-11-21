import { apiClient } from '../http';
import { SecurityUtils } from '../../utils/security';

export const productAPI = {
  async getProducts(params = {}) {
    const queryString = new URLSearchParams();
    Object.keys(params).forEach(key => {
      const value = params[key];
      if (value !== null && value !== undefined && value !== '') {
        const sanitized = typeof value === 'string' ? SecurityUtils.sanitizeInput(value) : value;
        queryString.append(key, sanitized);
      }
    });

    const url = `/products${queryString.toString() ? `?${queryString}` : ''}`;
    return await apiClient.request('GET', url);
  },

  async getProductDetail(productId) {
    return await apiClient.request('GET', `/products/${productId}`);
  },

  async searchProducts(keyword, filters = {}) {
    const params = { keyword, ...filters };
    return this.getProducts(params);
  }
};