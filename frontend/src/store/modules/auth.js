import { authAPI } from '../../services/api/authAPI';
import { apiClient } from '../../services/http';

const storedUser = (() => {
  try {
    return JSON.parse(localStorage.getItem('current_user')) || null;
  } catch {
    return null;
  }
})();

const SESSION_REFRESH_INTERVAL = 10 * 60 * 1000; // 10分钟自动同步会话
let refreshTimerId = null;

const state = {
  isAuthenticated: !!localStorage.getItem('access_token'),
  user: storedUser,
  token: localStorage.getItem('access_token'),
  loading: false,
  error: null
};

const mutations = {
  SET_AUTH_DATA(state, { user, token }) {
    state.isAuthenticated = true;
    state.user = user;
    if (token) {
      state.token = token;
      localStorage.setItem('access_token', token);
      apiClient.setToken(token);
    }
    localStorage.setItem('current_user', JSON.stringify(user || null));
  },
  SET_USER_PROFILE(state, user) {
    state.user = user;
    if (user) {
      localStorage.setItem('current_user', JSON.stringify(user));
    }
  },
  CLEAR_AUTH_DATA(state) {
    state.isAuthenticated = false;
    state.user = null;
    state.token = null;
    state.error = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
  },
  SET_LOADING(state, loading) {
    state.loading = loading;
  },
  SET_ERROR(state, error) {
    state.error = error;
  },
  CLEAR_ERROR(state) {
    state.error = null;
  }
};

const actions = {
  async initializeAuth({ state, dispatch }) {
    if (!state.token) {
      return;
    }
    apiClient.setToken(state.token);
    try {
      await dispatch('fetchProfile', { silent: true });
      dispatch('scheduleSessionRefresh');
    } catch (error) {
      await dispatch('logout');
      console.warn('初始化会话失败:', error.message);
    }
  },
  scheduleSessionRefresh({ state, dispatch }) {
    if (!state.token) {
      return;
    }
    if (refreshTimerId) {
      clearInterval(refreshTimerId);
    }
    refreshTimerId = setInterval(() => {
      dispatch('refreshSession');
    }, SESSION_REFRESH_INTERVAL);
  },
  cancelSessionRefresh() {
    if (refreshTimerId) {
      clearInterval(refreshTimerId);
      refreshTimerId = null;
    }
  },
  async refreshSession({ dispatch }) {
    try {
      await dispatch('fetchProfile', { silent: true });
    } catch (error) {
      console.warn('会话刷新失败，自动登出:', error.message);
      await dispatch('logout');
    }
  },
  async login({ commit, dispatch }, credentials) {
    commit('SET_LOADING', true);
    commit('CLEAR_ERROR');
    try {
      const response = await authAPI.login(credentials);
      if (response.code !== 0) {
        throw new Error(response.message || '登录失败');
      }
      commit('SET_AUTH_DATA', {
        user: response.data.user,
        token: response.data.token
      });
      dispatch('scheduleSessionRefresh');
      return { success: true, data: response.data };
    } catch (error) {
      commit('SET_ERROR', error.message);
      return { success: false, error: error.message };
    } finally {
      commit('SET_LOADING', false);
    }
  },
  async register({ commit }, userData) {
    commit('SET_LOADING', true);
    commit('CLEAR_ERROR');
    try {
      const response = await authAPI.register(userData);
      if (response.code !== 0) {
        throw new Error(response.message || '注册失败');
      }
      return { success: true, data: response.data };
    } catch (error) {
      commit('SET_ERROR', error.message);
      return { success: false, error: error.message };
    } finally {
      commit('SET_LOADING', false);
    }
  },
  async logout({ commit, dispatch }) {
    try {
      await authAPI.logout();
    } catch (error) {
      console.warn('登出请求失败：', error.message);
    } finally {
      dispatch('cancelSessionRefresh');
      apiClient.removeToken();
      commit('CLEAR_AUTH_DATA');
    }
  },
  async fetchProfile({ commit, state }, { silent = false } = {}) {
    if (!state.token) {
      return { success: false, error: '尚未登录' };
    }
    if (!silent) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
    }
    try {
      const response = await authAPI.getProfile();
      if (response.code !== 0 || !response.data) {
        throw new Error(response.message || '获取用户信息失败');
      }
      commit('SET_USER_PROFILE', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      if (!silent) {
        commit('SET_ERROR', error.message);
      }
      throw error;
    } finally {
      if (!silent) {
        commit('SET_LOADING', false);
      }
    }
  },
  clearError({ commit }) {
    commit('CLEAR_ERROR');
  }
};

const getters = {
  isAuthenticated: state => state.isAuthenticated,
  currentUser: state => state.user,
  authLoading: state => state.loading,
  authError: state => state.error,
  authToken: state => state.token
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
};
