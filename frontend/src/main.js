import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import store from './store';
import { errorMonitor } from './utils/errorMonitor';

// 导入全局样式
import './styles/main.css';
import './styles/responsive.css';

errorMonitor.init();

const app = createApp(App);

app.use(store);
app.use(router);

store.dispatch('auth/initializeAuth').finally(() => {
  app.mount('#app');
});