<template>
  <form class="login-form" @submit.prevent="submit">
    <template v-if="!mfa && !recoveryCodes.length">
      <label for="username">用户名或邮箱</label><input id="username" v-model.trim="username" autocomplete="username" required maxlength="50" />
      <label for="password">密码</label><input id="password" v-model="password" type="password" autocomplete="current-password" required maxlength="128" />
      <p class="hint">管理员和审计员需要在下一步验证动态码。</p>
      <button :disabled="loading">{{ loading ? '正在验证…' : '登录' }}</button>
      <button type="button" class="secondary" :disabled="loading" @click="certLogin">浏览器证书登录</button>
      <div class="links"><router-link to="/forgot-password">忘记密码</router-link><router-link to="/register">注册账号</router-link></div>
    </template>
    <template v-else-if="mfa">
      <h2>{{ mfa.enrollment_required ? '绑定身份验证器' : '双因素验证' }}</h2>
      <template v-if="mfa.enrollment_required"><TotpQrCode :uri="mfa.provisioning_uri" /><p class="hint">也可以手动添加账号，选择“基于时间”，输入以下密钥，再填写六位动态码。</p><code class="secret">{{ mfa.secret }}</code><button type="button" class="secondary" @click="copySecret">复制绑定密钥</button></template>
      <p v-else class="hint">输入身份验证器的六位动态码。设备遗失时，可使用一枚未使用的恢复码登录。</p>
      <label for="code">{{ mfa.enrollment_required ? '动态验证码' : '动态验证码或恢复码' }}</label><input id="code" v-model.trim="code" autocomplete="one-time-code" required maxlength="32" />
      <button :disabled="loading">{{ loading ? '正在验证…' : '验证并登录' }}</button>
      <button type="button" class="secondary" :disabled="loading" @click="reset">返回账号登录</button>
      <p class="hint">验证窗口为 5 分钟；请保持设备时间准确。连续失败 5 次会锁定 15 分钟。</p>
    </template>
    <template v-else>
      <h2>保存恢复码</h2><p class="hint">恢复码仅显示一次，每枚只能使用一次。请妥善保存，以便设备丢失时登录。</p><pre class="secret">{{ recoveryCodes.join('\n') }}</pre>
      <button type="button" class="secondary" @click="downloadCodes">下载恢复码</button>
      <label class="check"><input v-model="saved" type="checkbox" />我已妥善保存恢复码</label><button type="button" :disabled="!saved" @click="finish">进入后台</button>
    </template>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" class="hint" role="status">{{ notice }}</p>
  </form>
</template>
<script setup>
import { ref } from 'vue';
import TotpQrCode from './TotpQrCode.vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import { apiClient } from '../../services/http';
const store = useStore(), router = useRouter();
const username = ref(''), password = ref(''), code = ref(''), error = ref(''), notice = ref('');
const loading = ref(false), mfa = ref(null), recoveryCodes = ref([]), saved = ref(false);
const reset = () => { mfa.value = null; code.value = ''; error.value = ''; notice.value = ''; };
const finish = () => {
  mfa.value = null; recoveryCodes.value = []; password.value = '';
  const user = store.getters['auth/currentUser'];
  const destination = ['admin', 'auditor', 'merchant'].includes(user?.role || user?.user_role) ? '/dashboard' : '/products';
  const requested = router.currentRoute.value.query.redirect;
  router.push(typeof requested === 'string' && requested.startsWith('/') && !requested.startsWith('//') ? requested : destination);
};
const accept = result => { password.value = ''; if (result.mfa) { mfa.value = result.mfa; return; } if (result.success) finish(); else error.value = result.error || '登录失败'; };
async function submit() {
  error.value = ''; notice.value = ''; loading.value = true;
  try {
    if (!mfa.value) accept(await store.dispatch('auth/login', { username: username.value, password: password.value }));
    else {
      const response = await apiClient.request('POST', '/auth/mfa/verify', { challenge: mfa.value.challenge, code: code.value });
      if (response.code !== 0) throw new Error(response.message);
      store.commit('auth/SET_AUTH_DATA', response.data); store.dispatch('auth/scheduleSessionRefresh');
      mfa.value = null; code.value = ''; recoveryCodes.value = response.data.recovery_codes || [];
      if (!recoveryCodes.value.length) finish();
    }
  } catch (e) { error.value = e.message; } finally { loading.value = false; }
}
async function certLogin() { error.value = ''; loading.value = true; try { accept(await store.dispatch('auth/certMtlsLogin', username.value)); } catch (e) { error.value = e.message; } finally { loading.value = false; } }
async function copySecret() { try { await navigator.clipboard.writeText(mfa.value.secret); notice.value = '已复制，请粘贴到身份验证器中'; } catch { error.value = '无法访问剪贴板，请手动复制密钥'; } }
function downloadCodes() { const url = URL.createObjectURL(new Blob([recoveryCodes.value.join('\n')], { type: 'text/plain' })); const a = document.createElement('a'); a.href = url; a.download = 'recovery-codes.txt'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
</script>
<style scoped>
.login-form{max-width:420px;margin:auto;padding:24px;display:grid;gap:14px}label{font-weight:600;color:#26354a}input{width:100%;border:1px solid #cbd5e1;border-radius:8px;padding:12px;font:inherit}input:focus{outline:2px solid #599dd8;outline-offset:2px}button{padding:12px;border:0;border-radius:8px;background:#2059b5;color:white;font:inherit;cursor:pointer}button:disabled{opacity:.5;cursor:wait}.secondary{background:#edf2f8;color:#294364}.hint{color:#65758b;font-size:13px;line-height:1.7}.secret{background:#f1f5f9;padding:14px;overflow-wrap:anywhere;white-space:pre-wrap;font-size:13px}.error{background:#fff0ef;color:#b42318;padding:12px;border-radius:6px}.links{display:flex;justify-content:space-between;font-size:14px}.check{display:flex;gap:8px;align-items:center;font-size:13px}.check input{width:auto}
</style>
