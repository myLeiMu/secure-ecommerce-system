// Test helper: use the exact browser encryption module; JSON on stdin only.
const { webcrypto } = require('node:crypto');
if (!globalThis.crypto) globalThis.crypto = webcrypto;
let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', async () => {
  try {
    const { seal } = await import('../frontend/src/services/tunnelCrypto.mjs');
    const data = JSON.parse(input);
    console.log(JSON.stringify(await seal(data.body, data.info, data.method || 'POST',
      data.path || '/api/tunnel/demo', data.authorization, data.options || {})));
  } catch (err) { console.error(err.message); process.exitCode = 1; }
});
