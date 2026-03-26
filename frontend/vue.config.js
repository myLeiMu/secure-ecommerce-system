const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 3000,
    host: '0.0.0.0', 
    allowedHosts: 'all',
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
