const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('file://' + path.resolve('/home/user/GestionBiblioteca/mockup_preview.html'));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/home/user/GestionBiblioteca/preview.png', fullPage: false });
  await browser.close();
  console.log('Screenshot saved.');
})();
