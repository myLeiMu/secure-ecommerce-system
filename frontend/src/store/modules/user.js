import { userAPI } from '../../services/api/userAPI';
import { SecurityUtils } from '../../utils/security';

const state = {
  profile: null,
  loading: false,
  error: null,
  successMessage: ''
};

const mutations = {
  SET_USER_PROFILE(state, profile) {
    state.profile = profile;
  },
  UPDATE_PROFILE(state, updates) {
    if (state.profile) {
      state.profile = { ...state.profile, ...updates };
    }
  },
  SET_LOADING(state, loading) {
    state.loading = loading;
  },
  SET_ERROR(state, error) {
    state.error = error;
  },
  SET_SUCCESS(state, message) {
    state.successMessage = message;
  },
  CLEAR_FEEDBACK(state) {
    state.error = null;
    state.successMessage = '';
  }
};

const actions = {
  cacheProfile({ commit }, profile) {
    commit('SET_USER_PROFILE', profile);
  },
  async updateProfile({ commit }, profileData) {
    commit('SET_LOADING', true);
    commit('CLEAR_FEEDBACK');
    try {
      const payload = {
        username: SecurityUtils.sanitizeInput(profileData.username),
        email: SecurityUtils.sanitizeInput(profileData.email),
        phone: SecurityUtils.sanitizeInput(profileData.phone)
      };
      const response = await userAPI.updateProfile(payload);
      if (response.code !== 0) {
        throw new Error(response.message || '更新个人资料失败');
      }
      commit('UPDATE_PROFILE', payload);
      commit('SET_SUCCESS', '个人资料已更新');
      return { success: true };
    } catch (error) {
      commit('SET_ERROR', error.message);
      return { success: false, error: error.message };
    } finally {
      commit('SET_LOADING', false);
    }
  },
  async changePassword({ commit }, passwordData) {
    commit('SET_LOADING', true);
    commit('CLEAR_FEEDBACK');
    try {
      const payload = {
        old_password: passwordData.oldPassword,
        new_password: passwordData.newPassword
      };
      const response = await userAPI.changePassword(payload);
      if (response.code !== 0) {
        throw new Error(response.message || '修改密码失败');
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    } finally {
      commit('SET_LOADING', false);
    }
  },
  clearFeedback({ commit }) {
    commit('CLEAR_FEEDBACK');
  }
};

const getters = {
  userProfile: state => state.profile,
  userLoading: state => state.loading,
  userError: state => state.error,
  userSuccess: state => state.successMessage
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
};
