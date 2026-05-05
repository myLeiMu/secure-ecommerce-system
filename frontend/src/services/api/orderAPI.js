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
  },

  async deleteOrder(orderId) {
    return await apiClient.request('DELETE', `/orders/${orderId}/delete`);
  },

  async startBankPay(orderId) {
    return await apiClient.request('POST', `/orders/${orderId}/pay`);
  },

  async parsePaymentResult(payload) {
    return await apiClient.request('POST', '/pay/sync-result', payload);
  }
};
