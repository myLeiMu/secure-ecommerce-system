<template>
  <figure class="totp-qr">
    <template v-if="qr">
      <svg :viewBox="`0 0 ${qr.size} ${qr.size}`" role="img" aria-label="身份验证器绑定二维码" shape-rendering="crispEdges">
        <rect width="100%" height="100%" fill="white" />
        <path :d="qr.path" fill="black" />
      </svg>
      <figcaption>用身份验证器扫描二维码，然后输入生成的六位动态码完成绑定。</figcaption>
    </template>
    <p v-else role="status">二维码暂不可用，请使用下方密钥手动绑定。</p>
  </figure>
</template>

<script setup>
import { computed } from 'vue';
import QRCode from 'qrcode';

const props = defineProps({ uri: { type: String, default: '' } });
// Encode locally: the provisioning URI contains the secret and must not go to a QR service.
const qr = computed(() => {
  if (!props.uri.startsWith('otpauth://totp/')) return null;
  try {
    const { modules } = QRCode.create(props.uri, { errorCorrectionLevel: 'M' });
    const segments = [];
    for (let row = 0; row < modules.size; row++) {
      for (let col = 0; col < modules.size; col++) {
        if (modules.get(row, col)) segments.push(`M${col + 4} ${row + 4}h1v1h-1z`);
      }
    }
    return { size: modules.size + 8, path: segments.join('') };
  } catch {
    return null;
  }
});
</script>

<style scoped>
.totp-qr{margin:0;display:grid;justify-items:center;gap:12px}
svg{display:block;width:240px;max-width:100%;height:auto;background:#fff;border:1px solid #e9ecef;border-radius:8px}
figcaption,p{font-size:13px;color:#65758b;line-height:1.7;text-align:center}
</style>
