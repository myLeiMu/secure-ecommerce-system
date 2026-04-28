import { apiClient } from '../http';

export const cartAPI = {
  async getCart() {
    return await apiClient.request('GET', '/cart');
  },

  async addToCart(payload) {
    return await apiClient.request('POST', '/cart', payload);
  },

  async updateCartItem(productId, payload) {
    return await apiClient.request('PUT', `/cart/items/${productId}`, payload);
  },

  async removeCartItem(productId) {
    return await apiClient.request('DELETE', `/cart/items/${productId}`);
  }
};
