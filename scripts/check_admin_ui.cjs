// Run against scripts/preview_course.py. Requires Playwright and Chromium.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const output = path.resolve(__dirname, '../docs/evidence');
fs.mkdirSync(output, { recursive: true });
function totp(secret) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret].map(c => alphabet.indexOf(c).toString(2).padStart(5, '0')).join('');
  const key = Buffer.from(bits.match(/.{8}/g).map(b => parseInt(b, 2)));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const h = crypto.createHmac('sha1', key).update(counter).digest();
  return ((h.readUInt32BE(h[19] & 15) & 0x7fffffff) % 1000000).toString().padStart(6, '0');
}
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_EXECUTABLE ? { executablePath: process.env.CHROME_EXECUTABLE } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  const errors = [], actions = [];
  async function checkDialog(name) {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 844 });
      const dialog = page.getByRole('dialog');
      await dialog.waitFor();
      const layout = await dialog.evaluate(el => {
        const box = el.getBoundingClientRect();
        const footer = el.querySelector('footer').getBoundingClientRect();
        return { fits: box.left >= 0 && box.right <= innerWidth && box.top >= 0 && box.bottom <= innerHeight,
          footerVisible: footer.bottom <= innerHeight, noOverflow: el.scrollWidth <= el.clientWidth };
      });
      if (!layout.fits || !layout.footerVisible || !layout.noOverflow) throw new Error(`${name}: invalid dialog layout at ${width}`);
      await page.screenshot({ path: path.join(output, `dialog-${name}-${width}.png`) });
    }
    await page.setViewportSize({ width: 1440, height: 1050 });
  }

  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8765/login');
  await page.locator('#username').fill('user3');
  await page.locator('#password').fill('TestPass123!');
  await page.locator('.login-form button[type=submit], .login-form button:not([type])').first().click();
  await page.getByRole('heading', { name: '绑定身份验证器' }).waitFor();
  await page.locator('#code').fill(totp(await page.locator('code.secret').textContent()));
  await page.getByRole('button', { name: '验证并登录', exact: true }).click();
  await page.getByRole('heading', { name: '保存恢复码' }).waitFor();
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: '进入后台', exact: true }).click();
  await page.getByRole('heading', { name: '运营概览', exact: true }).waitFor();
  await page.locator('.metrics article').first().waitFor();
  await page.screenshot({ path: path.join(output, 'admin-overview.png'), fullPage: true });
  actions.push('Password + TOTP enrollment and recovery-code acknowledgement');
  await page.locator('.console-nav').getByRole('button', { name: '用户管理' }).click();
  await page.getByText('u1@example.com', { exact: true }).waitFor();
  await page.locator('tr').filter({ hasText: 'u1@example.com' }).getByRole('button', { name: '管理权限' }).click();
  await checkDialog('user');
  await page.locator('.admin-dialog select').first().selectOption('auditor');
  await page.getByRole('button', { name: '保存修改', exact: true }).click();
  await page.locator('.admin-dialog').waitFor({ state: 'hidden' });
  actions.push('User role saved through authenticated PATCH');
  await page.locator('.console-nav').getByRole('button', { name: '商品管理' }).click();
  await page.getByRole('button', { name: '新增商品' }).click();
  await checkDialog('product');
  await page.getByLabel('商品名称', { exact: true }).fill('浏览器联调商品');
  await page.getByLabel('SKU', { exact: true }).fill('UI-SKU-001');
  await page.getByLabel('分类', { exact: true }).selectOption('1');
  await page.getByLabel('售价（元）', { exact: true }).fill('29.90');
  await page.getByLabel('库存', { exact: true }).fill('25');
  await page.getByRole('button', { name: '保存修改', exact: true }).click();
  await page.locator('.admin-dialog').waitFor({ state: 'hidden' });
  await page.getByText('浏览器联调商品', { exact: true }).waitFor();
  await page.screenshot({ path: path.join(output, 'admin-products.png'), fullPage: true });
  actions.push('Product created and displayed from database');
  await page.locator('.console-nav').getByRole('button', { name: '分类管理' }).click();
  await page.getByRole('button', { name: '新增分类' }).click();
  await checkDialog('category');
  await page.getByRole('button', { name: '取消', exact: true }).click();

  await page.locator('.console-nav').getByRole('button', { name: '订单管理' }).click();
  await page.getByRole('button', { name: '发货', exact: true }).click();
  await checkDialog('order');
  await page.getByLabel('物流单号', { exact: true }).fill('UI-TRACK-001');
  await page.getByRole('button', { name: '确认发货', exact: true }).click();
  await page.getByText('UI-TRACK-001', { exact: true }).waitFor();
  actions.push('Paid order shipped with tracking number');
  await page.locator('.console-nav').getByRole('button', { name: '日志与安全事件' }).click();
  await page.getByText('orders.ship', { exact: true }).waitFor();
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出审计报告' }).click();
  const download = await downloadEvent;
  if (download.suggestedFilename() !== 'audit-report.json') throw new Error('Audit export missing');
  await page.screenshot({ path: path.join(output, 'admin-audit.png'), fullPage: true });
  actions.push('Audit records queried and report downloaded');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, 'admin-mobile.png'), fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  if (overflow) errors.push('Mobile viewport has horizontal overflow');
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('http://127.0.0.1:8765/products');
    const entry = page.getByRole('link', { name: '控制台', exact: true });
    await entry.waitFor();
    if (await entry.count() !== 1) throw new Error('Duplicate dashboard entry on catalog');
    await entry.click();
    await page.getByRole('heading', { name: '运营概览', exact: true }).waitFor();
    if (await page.getByRole('link', { name: '控制台', exact: true }).count() !== 1) throw new Error('Duplicate dashboard entry on dashboard');
    await page.locator('.console-nav').getByRole('button', { name: '账号安全' }).click();
    await page.getByRole('heading', { name: '更换身份验证器' }).waitFor();
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Security page overflows viewport');
    await page.screenshot({ path: path.join(output, `admin-security-${width}.png`), fullPage: true });
  }
  actions.push('Single dashboard entry and account-security layout at desktop and mobile widths');
  fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({ actions, errors }, null, 2));
  await browser.close();
  if (errors.length) throw new Error(errors.join('\n'));
  console.log(JSON.stringify({ passed: actions.length, errors }));
})().catch(error => { console.error(error); process.exit(1); });
