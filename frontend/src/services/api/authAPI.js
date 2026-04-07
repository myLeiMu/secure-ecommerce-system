import { apiClient } from '../http';

export const authAPI = {
  async login(credentials) {
    let response;
    try {
      response = await apiClient.request('POST', '/auth/login', credentials, { timeout: 30000 });
    } catch (error) {
      const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (!error.isNetworkError || !isLocalHost) {
        throw error;
      }
      response = await apiClient.client.request({
        method: 'POST',
        url: 'http://127.0.0.1:8080/api/auth/login',
        data: credentials,
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json'
        }
      }).then((res) => res.data);
    }
    if (response.code === 0 && response.data.token) {
      apiClient.setToken(response.data.token);
    }
    return response;
  },

  async register(userData) {
    return await apiClient.request('POST', '/users/register', userData);
  },

  async certChallenge(username) {
    return await apiClient.request('POST', '/auth/cert/challenge', { username });
  },

  async certLogin(payload) {
    const response = await apiClient.request('POST', '/auth/cert/login', payload, { timeout: 30000 });
    if (response.code === 0 && response.data?.token) {
      apiClient.setToken(response.data.token);
    }
    return response;
  },

  async certMtlsLogin(username) {
    let response;
    try {
      response = await apiClient.request('POST', '/auth/cert/mtls-login', username ? { username } : {});
    } catch (error) {
      const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (!error.isNetworkError || !isLocalHost) {
        throw error;
      }
      response = await apiClient.client.request({
        method: 'POST',
        url: 'https://localhost:8443/api/auth/cert/mtls-login',
        data: username ? { username } : {},
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json'
        }
      }).then((res) => res.data);
    }
    if (response.code === 0 && response.data?.token) {
      apiClient.setToken(response.data.token);
    }
    return response;
  },

  async certFileLogin(payload) {
    const response = await apiClient.request('POST', '/auth/cert/file-login', payload, { timeout: 30000 });
    if (response.code === 0 && response.data?.token) {
      apiClient.setToken(response.data.token);
    }
    return response;
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
