import { seal, protectedRequest } from './tunnelCrypto.cjs';

export function installTunnel(client) {
  client.interceptors.request.use(async config => {
    const method = (config.method || 'GET').toUpperCase();
    const path = new URL(client.getUri(config), window.location.origin).pathname;
    if (!protectedRequest(method, path)) return config;
    // Fetch on each request so rotation is observed; never retry as plaintext.
    const response = await client.get('/tunnel/key');
    const info = response.data.data;
    config.data = await seal(config.data, info, method, path, config.headers.Authorization || '');
    config.headers['Content-Type'] = 'application/json';
    return config;
  });
}
