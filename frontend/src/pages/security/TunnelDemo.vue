<template>
  <main class="tunnel-page">
    <header><p class="eyebrow">SECURITY LAB · WEEK 04</p><h1>收件信息安全传输</h1>
      <p>使用虚构收件信息演示加密传输与防重放，不会创建订单或保存地址。</p></header>
    <div class="demo-grid">
      <section class="card">
        <h2>模拟交易收件信息</h2>
        <form @submit.prevent="submit">
          <label>收件人<input v-model.trim="form.recipient" maxlength="200" required autocomplete="off" /></label>
          <label>手机号<input v-model.trim="form.phone" maxlength="20" required autocomplete="off" /></label>
          <label>收件地址<textarea v-model.trim="form.address" maxlength="200" required rows="3"></textarea></label>
          <button :disabled="busy">{{ busy ? '正在安全提交…' : '加密并发送演示请求' }}</button>
        </form>
      </section>
      <section class="card" aria-live="polite">
        <h2>验证结果</h2>
        <p v-if="!result && !error" class="muted">提交后显示服务器验证结果。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <template v-if="result">
          <p class="success">{{ result.message }}</p>
          <dl><dt>服务端解密出的手机号（脱敏）</dt><dd>{{ result.data.phone_masked }}</dd>
            <dt>解密数据摘要 SHA-256</dt><dd class="hash">{{ result.data.plaintext_sha256 }}</dd></dl>
        </template>
        <div class="hint"><h3>课堂抓包提示</h3><p>打开开发者工具 Network，检查 POST /api/tunnel/demo：请求体只有密文、密钥封装、时间戳和 nonce。可在 Burp Repeater 原样重放，预期返回 409。</p>
          <p>采用 SM2 + SM4-GCM；HTTPS 和账号权限检查仍然生效。每次点击会生成新密钥、新 nonce。</p></div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { apiClient } from '../../services/http';
const form = reactive({ recipient: '课堂测试用户', phone: '13800001234', address: '演示校区测试路 1 号（虚构地址）' });
const busy = ref(false), result = ref(null), error = ref('');
async function submit() {
  busy.value = true; result.value = null; error.value = '';
  try { result.value = await apiClient.request('POST', '/tunnel/demo', { ...form }); }
  catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}
</script>

<style scoped>
.tunnel-page{max-width:1100px;margin:0 auto;padding:36px 24px 64px;color:#20304a}header{margin-bottom:28px}h1{font-size:30px;margin:8px 0 12px}header p,.muted{color:#64748b;line-height:1.7}.eyebrow{font-size:12px;letter-spacing:2px;color:#2563eb}.demo-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:28px;box-shadow:0 8px 28px #0f172a06}h2{font-size:19px;margin:0 0 24px}form{display:grid;gap:20px}label{display:grid;gap:8px;font-size:14px;font-weight:600}input,textarea{box-sizing:border-box;width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;font:inherit;resize:vertical}input:focus,textarea:focus{outline:2px solid #bfdbfe;border-color:#3b82f6}button{border:0;border-radius:8px;background:#2563eb;color:white;padding:13px;font:inherit;cursor:pointer}button:disabled{opacity:.6;cursor:wait}.hint{background:#f8fafc;border-radius:10px;padding:16px;margin-top:28px;color:#64748b;font-size:14px;line-height:1.8}.hint h3{margin:0;color:#334155;font-size:14px}.hint p:last-child{margin-bottom:0}.success{color:#15803d;line-height:1.7}.error{color:#b91c1c}dt{color:#64748b;font-size:13px;margin-top:20px}dd{margin:8px 0}.hash{overflow-wrap:anywhere;font-family:monospace;line-height:1.7}@media(max-width:720px){.demo-grid{grid-template-columns:1fr}.tunnel-page{padding:24px 16px}.card{padding:20px}h1{font-size:25px}}
</style>
