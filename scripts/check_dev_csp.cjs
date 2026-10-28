const { chromium } = require('../frontend/node_modules/playwright');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ ignoreHTTPSErrors: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.exposeFunction('cspError', directive => errors.push(directive));
    await page.addInitScript(() => document.addEventListener('securitypolicyviolation', e => window.cspError(e.violatedDirective)));
    await page.goto('https://localhost:3000/login');
    await page.locator('#username').waitFor();
    const styles = await page.evaluate(() => [...document.querySelectorAll('style')].every(el => Boolean(el.nonce)));
    await page.getByRole('button', { name: /证书登录/ }).click();
    await page.waitForURL('https://localhost:8443/login');
    await page.locator('#username').waitFor();
    const result = { devStylesHaveNonce: styles, certificateButtonRoutesToMTLS: true, errors };
    fs.writeFileSync('docs/evidence/remediation-20261021/dev-browser.json', JSON.stringify(result, null, 2));
    if (!styles || errors.length) throw new Error(JSON.stringify(result));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
