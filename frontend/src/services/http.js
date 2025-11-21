import axios from 'axios';

class APIClient {
  constructor() {
    this.baseURL = process.env.VUE_APP_API_BASE_URL || '/api';
    this.token = localStorage.getItem('access_token');
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 15000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (this.token) {
      this.client.defaults.headers.common.Authorization = `Bearer ${this.token}`;
    }
  }

  async request(method, url, data = null, config = {}) {
    try {
      const response = await this.client.request({
        method,
        url,
        data,
        ...config
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  handleError(error) {
    if (error.response) {
      const { status, data } = error.response;
      if (status === 401) {
        this.handleUnauthorized();
        throw new Error(data?.message || '认证已过期，请重新登录');
      }
      if (status === 429) {
        throw new Error('请求频率过高，请稍后重试');
      }
      throw new Error(data?.message || '请求失败');
    }

    if (error.request) {
      throw new Error('网络连接失败，请检查网络设置');
    }

    throw new Error('请求配置错误');
  }

  handleUnauthorized() {
    this.removeToken();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  setToken(token) {
    this.token = token;
    if (token) {
      this.client.defaults.headers.common.Authorization = `Bearer ${token}`;
      localStorage.setItem('access_token', token);
    } else {
      delete this.client.defaults.headers.common.Authorization;
    }
  }

  removeToken() {
    this.token = null;
    delete this.client.defaults.headers.common.Authorization;
    localStorage.removeItem('access_token');
  }
}

export const apiClient = new APIClient();
