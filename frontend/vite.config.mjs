import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
const noncePlaceholder = '__RESPONSE_CSP_NONCE__';
const policy = (nonce, port = 3000) => [
  "default-src 'none'",
  `script-src 'self'${nonce ? ` 'nonce-${nonce}'` : ''}`,
  "script-src-attr 'none'",
  `style-src 'self'${nonce ? ` 'nonce-${nonce}'` : ''}`,
  "style-src-attr 'none'",
  "img-src 'self' https: http: data: blob:",
  "font-src 'self' data:",
  `connect-src 'self' wss://localhost:${port} wss://127.0.0.1:${port}`,
  "form-action 'self'", "frame-ancestors 'none'", "base-uri 'self'", "object-src 'none'"
].join('; ');

function responseSecurity() {
  return {
    name: 'response-security',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!/^(localhost|127\.0\.0\.1)(:\d+)?$/i.test(req.headers.host || req.headers[':authority'] || '')) {
          res.statusCode = 403;
          res.end('Invalid Host header');
          return;
        }
        // A new nonce for every HTML response; Vite uses its meta tag for HMR styles.
        const nonce = randomBytes(24).toString('base64');
        res.setHeader('Content-Security-Policy', policy(nonce, server.config.server.port));
        res.setHeader('X-Frame-Options', 'DENY');
        res.setHeader('X-Content-Type-Options', 'nosniff');
        res.setHeader('Referrer-Policy', 'no-referrer');
        res.setHeader('Strict-Transport-Security', 'max-age=86400');
        const end = res.end;
        res.end = function (data, ...args) {
          if (data && String(res.getHeader('Content-Type')).includes('text/html')) {
            data = Buffer.from(data.toString().replaceAll(noncePlaceholder, nonce));
            res.setHeader('Content-Length', data.length);
            res.setHeader('Cache-Control', 'no-store');
          }
          return end.call(this, data, ...args);
        };
        next();
      });
    }
  };
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, root, 'VUE_APP_');
  const port = Number(process.env.FRONTEND_DEV_PORT || loadEnv(mode, root, 'FRONTEND_DEV_PORT').FRONTEND_DEV_PORT || 3000);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('FRONTEND_DEV_PORT must be an integer between 1024 and 65535');
  // Server-side only: never expose this value through Vite define/import.meta.env.
  const gatewaySecret = loadEnv(mode, fileURLToPath(new URL('..', import.meta.url)), 'MTLS_PROXY_SECRET').MTLS_PROXY_SECRET;
  if (command === 'serve' && !gatewaySecret) throw new Error('MTLS_PROXY_SECRET is required for the HTTPS API proxy');
  const https = command === 'serve' ? {
    key: readFileSync(new URL('../keys/mtls_local/localhost.key', import.meta.url)),
    cert: readFileSync(new URL('../keys/mtls_local/localhost.crt', import.meta.url))
  } : undefined;
  return {
    plugins: [vue(), responseSecurity()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    define: {
      'process.env.VUE_APP_API_BASE_URL': JSON.stringify('/api'),
      'process.env.VUE_APP_ERROR_WEBHOOK': JSON.stringify(env.VUE_APP_ERROR_WEBHOOK || '')
    },
    html: command === 'serve' ? { cspNonce: noncePlaceholder } : {},
    server: {
      host: '127.0.0.1', port, strictPort: true, https,
      allowedHosts: ['localhost', '127.0.0.1'], cors: false,
      proxy: { '/api': { target: 'http://127.0.0.1:8080', changeOrigin: false, timeout: 30000,
        configure(proxy) {
          proxy.on('proxyReq', (proxyReq, req) => {
            // Dev HTTPS is not a client-certificate gateway; discard spoofed identity.
            for (const header of ['x-forwarded-host', 'forwarded', 'x-ssl-client-verify',
              'x-ssl-client-cert', 'x-ssl-client-s-dn', 'x-client-cert-pem']) proxyReq.removeHeader(header);
            proxyReq.setHeader('X-MTLS-PROXY-SECRET', gatewaySecret);
            proxyReq.setHeader('X-Forwarded-Proto', 'https');
            proxyReq.setHeader('X-Forwarded-For', req.socket.remoteAddress);
          });
        }
      } }
    },
    preview: {
      host: '127.0.0.1', port, strictPort: true, https,
      headers: { 'Content-Security-Policy': policy(undefined, port), 'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
        'Strict-Transport-Security': 'max-age=86400' }
    },
    build: { sourcemap: false },
    css: { devSourcemap: false }
  };
});
