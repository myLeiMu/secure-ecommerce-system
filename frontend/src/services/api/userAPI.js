import { apiClient } from '../http';

export const userAPI = {
  async updateProfile(profileData) {
    return await apiClient.request('PUT', '/users/profile', profileData);
  },

  async changePassword(passwordData) {
    return await apiClient.request('POST', '/users/change-password', passwordData);
  },

  async sendResetCode(payload) {
    return await apiClient.request('POST', '/users/send-reset-code', payload);
  },

  async resetPassword(payload) {
    return await apiClient.request('POST', '/users/reset-password', payload);
  }
};