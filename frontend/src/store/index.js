import { createStore } from 'vuex';
import auth from './modules/auth';
import user from './modules/user';
import products from './modules/products';

export default createStore({
  modules: {
    auth,
    user,
    products
  },
  
  state: {
    appLoading: false
  },
  
  mutations: {
    SET_APP_LOADING(state, loading) {
      state.appLoading = loading;
    }
  },
  
  actions: {
    setAppLoading({ commit }, loading) {
      commit('SET_APP_LOADING', loading);
    }
  },
  
  getters: {
    appLoading: state => state.appLoading
  }
});