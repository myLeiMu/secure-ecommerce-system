const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const path = require('path');
const output = path.resolve(__dirname, '../docs/evidence/week4');
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROME_EXECUTABLE ? { executablePath: process.env.CHROME_EXECUTABLE } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('http://127.0.0.1:8767/login');
    await page.locator('#username').fill('user1');
    await page.locator('#password').fill('TestPass123!');
    await page.locator('.login-form button[type=submit], .login-form button:not([type])').first().click();
    await page.waitForURL(/products/);
    await page.goto('http://127.0.0.1:8767/tunnel-demo');
    const received = page.waitForResponse(r => r.url().endsWith('/api/tunnel/demo') && r.request().method() === 'POST');
    await page.getByRole('button', { name: '加密并发送演示请求' }).click();
    const response = await received;
    if (response.status() !== 200) throw new Error(await response.text());
    const envelope = response.request().postDataJSON();
    if (JSON.stringify(envelope).includes('13800001234')) throw new Error('Plaintext in request');
    await page.getByText('138****1234', { exact: true }).waitFor();
    await page.screenshot({ path: path.join(output, 'demo-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'demo-mobile.png'), fullPage: true });
    if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) throw new Error('Mobile overflow');
    // Replay through HTTP, retaining Authorization only in memory.
    const authorization = response.request().headers().authorization;
    const replay = await page.request.post('http://127.0.0.1:8767/api/tunnel/demo', {
      headers: { Authorization: authorization }, data: envelope });
    if (replay.status() !== 409) throw new Error('Replay was not rejected');
    fs.writeFileSync(path.join(output, 'browser-capture.json'), JSON.stringify({
      environment: 'Isolated localhost HTTP demo, real browser Axios interceptor (not nginx mTLS)',
      request: { method: 'POST', path: '/api/tunnel/demo', body: envelope },
      response: { status: response.status(), body: await response.json() },
      replay: { status: replay.status(), body: await replay.json() }, errors
    }, null, 2));
    if (errors.length) throw new Error(errors.join('\n'));
    console.log('PASS: browser encryption, HTTP replay rejection, desktop/mobile screenshots');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
