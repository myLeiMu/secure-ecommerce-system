import { apiClient } from '../http';

export const authAPI = {
  async login(credentials) {
    const response = await apiClient.request('POST', '/auth/login', credentials);
    if (response.code === 0 && response.data.token) {
      apiClient.setToken(response.data.token);
    }
    return response;
  },

  async register(userData) {
    return await apiClient.request('POST', '/users/register', userData);
  },

  async logout() {
    try {
      await apiClient.request('POST', '/auth/logout');
    } catch (error) {
      console.warn('登出请求失败:', error);
    } finally {
      apiClient.removeToken();
    }
  },

  async getProfile() {
    return await apiClient.request('GET', '/users/profile');
  }
};