const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 3000,
    host: '127.0.0.1',
    allowedHosts: ['localhost', '127.0.0.1'],
    headers: {
      'X-Frame-Options': 'DENY',
      'Content-Security-Policy': "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin'
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
        proxyTimeout: 30000,
        timeout: 30000
      }
    }
  },
  css: {
    sourceMap: true
  }
});
