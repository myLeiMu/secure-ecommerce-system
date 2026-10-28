// Run against scripts/week2_classroom.py --serve (fresh process). Requires Playwright and Chromium.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const output = path.resolve(__dirname, '../docs/evidence/week2');
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
  const page = await browser.newPage({ viewport: { width: 2000, height: 1050 } });
  const errors = [], actions = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8766/login');
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
  await page.locator('.console-nav').getByRole('button', { name: '角色权限' }).click();
  await page.getByRole('heading', { name: '角色权限矩阵' }).waitFor();
  if (await page.locator('tbody tr').count() !== 3) throw new Error('Expected three business roles');
  await page.screenshot({ path: path.join(output, 'role-matrix.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.locator('.console-nav').getByRole('button', { name: '日志与安全事件' }).click();
  await page.getByText('MFA_REPLAY', { exact: true }).first().waitFor();
  await page.getByText('MFA_FAILED', { exact: true }).first().waitFor();
  await page.getByText('MFA_SUCCESS', { exact: true }).first().waitFor();
  await page.screenshot({ path: path.join(output, 'mfa-audit.png'), fullPage: true });
  await browser.close();
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('PASS: three business roles and MFA audit screenshot');
})().catch(error => { console.error(error); process.exit(1); });
