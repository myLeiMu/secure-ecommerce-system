import { apiClient } from '../http';

export const orderAPI = {
  async createOrderFromCart(payload) {
    return await apiClient.request('POST', '/orders', payload);
  },

  async getMyOrders() {
    return await apiClient.request('GET', '/orders');
  },

  async getOrderDetail(orderId) {
    return await apiClient.request('GET', `/orders/${orderId}`);
  },

  async cancelOrder(orderId) {
    return await apiClient.request('POST', `/orders/${orderId}/cancel`);
  }
};
