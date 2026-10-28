<template>
  <div class="security-settings">
    <h2>更换身份验证器</h2>
    <p>设备丢失时，使用恢复码验证后重新绑定。开始更换会使原有会话失效；请在 5 分钟内完成绑定。完成后旧密钥和旧恢复码全部作废。</p>
    <form v-if="!codes.length" @submit.prevent="submit">
      <template v-if="!pending"><label for="current-factor">当前动态码或恢复码</label><input id="current-factor" v-model.trim="code" required maxlength="32" autocomplete="one-time-code" /></template>
      <template v-else><TotpQrCode :uri="pending.provisioning_uri" /><p>也可以在新身份验证器中手动添加以下密钥，选择基于时间的六位验证码。</p><code>{{ pending.secret }}</code><label for="new-factor">新设备动态码</label><input id="new-factor" v-model.trim="code" required pattern="[0-9]{6}" autocomplete="one-time-code" /></template>
      <button :disabled="busy">{{ busy ? '验证中…' : pending ? '确认新设备' : '验证并开始更换' }}</button>
    </form>
    <template v-else><h3>保存新的恢复码</h3><p>恢复码仅显示一次，请妥善保存。</p><pre>{{ codes.join('\n') }}</pre><button @click="download">下载恢复码</button><button @click="codes = []">已保存</button></template>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>
<script setup>
import { ref } from 'vue';
import TotpQrCode from './TotpQrCode.vue';
import { useStore } from 'vuex';
import { apiClient } from '../../services/http';
const store=useStore(),pending=ref(null),code=ref(''),codes=ref([]),busy=ref(false),error=ref('');
async function submit(){busy.value=true;error.value='';try{if(!pending.value){const r=await apiClient.request('POST','/auth/mfa/rebind',{code:code.value});pending.value=r.data;}else{const r=await apiClient.request('POST','/auth/mfa/verify',{challenge:pending.value.challenge,code:code.value});store.commit('auth/SET_AUTH_DATA',r.data);pending.value=null;codes.value=r.data.recovery_codes;}code.value='';}catch(e){error.value=e.message;}finally{busy.value=false;}}
function download(){const url=URL.createObjectURL(new Blob([codes.value.join('\n')],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='recovery-codes.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
</script>
<style scoped>
.security-settings{max-width:660px;padding:24px;border:1px solid #e9ecef;border-radius:8px;background:white}h2{font-size:20px;margin-bottom:18px}p{font-size:14px;color:#6c757d;line-height:1.9;margin:12px 0}form{display:grid;gap:14px}label{font-size:14px}input{padding:11px;border:1px solid #ddd;border-radius:4px;font:inherit}button{padding:10px 16px;background:#007bff;border:0;border-radius:4px;color:white;cursor:pointer;margin-right:10px}button:disabled{opacity:.5}code,pre{padding:15px;background:#f1f5fa;display:block;overflow-wrap:anywhere;white-space:pre-wrap;font-size:14px}.error{color:#b42318}
button:hover:not(:disabled){background:#0056b3}input:focus-visible,button:focus-visible{outline:2px solid #80bdff;outline-offset:2px}.security-settings{box-shadow:0 2px 8px rgba(0,0,0,.06)}
</style>
