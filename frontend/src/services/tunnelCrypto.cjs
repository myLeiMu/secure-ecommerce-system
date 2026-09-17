/* Shared by browser interceptor and Node interoperability tests. */
const { sm2, sm4 } = require('sm-crypto-v2');
const hex = bytes => Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
const protectedRequest = (method, path) => method.toUpperCase() === 'POST' &&
  ['/api/tunnel/demo', '/api/users/bank-card'].includes(path.replace(/\/$/, ''));

async function seal(data, info, method, path, authorization, options = {}) {
  if (!globalThis.crypto?.subtle || !globalThis.crypto?.getRandomValues) {
    throw new Error('安全通道需要 HTTPS 或 localhost 安全环境');
  }
  if (info.v !== 1 || !/^[0-9a-f]{16}$/.test(info.kid) || !/^04[0-9a-f]{128}$/.test(info.public_key)) {
    throw new Error('安全通道公钥无效');
  }
  const utf8 = new TextEncoder();
  const plaintext = utf8.encode(JSON.stringify(data));
  if (plaintext.length > 32768) throw new Error('安全通道请求不能超过 32 KiB');
  const key = globalThis.crypto.getRandomValues(new Uint8Array(16));
  const nonce = hex(globalThis.crypto.getRandomValues(new Uint8Array(12)));
  const envelope = { v: 1, kid: info.kid, ts: options.ts ?? Math.floor(Date.now() / 1000), nonce };
  const tokenHash = hex(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', utf8.encode(authorization))));
  const aad = utf8.encode([1, info.kid, method.toUpperCase(), path, envelope.ts, nonce, tokenHash].join('\n'));
  try {
    const result = sm4.encrypt(plaintext, key, { mode: 'gcm', iv: nonce,
      associatedData: aad, output: 'string', outputTag: true, padding: 'none' });
    return { ...envelope, encrypted_key: sm2.doEncrypt(key, info.public_key, 1),
      ciphertext: result.output, tag: result.tag };
  } finally {
    key.fill(0);
  }
}

module.exports = { seal, protectedRequest };
