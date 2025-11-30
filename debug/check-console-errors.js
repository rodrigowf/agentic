const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  // Collect console messages
  const logs = [];
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    logs.push({ type, text });
    console.log(`[${type.toUpperCase()}] ${text}`);
  });

  // Collect page errors
  page.on('pageerror', error => {
    console.error('[PAGE ERROR]', error.message);
  });

  try {
    await page.goto('http://localhost:3000', {
      waitUntil: 'networkidle0',
      timeout: 10000
    });

    // Wait a bit for React to mount
    await page.waitForTimeout(3000);

    console.log('\n=== Summary ===');
    console.log(`Total console messages: ${logs.length}`);
    console.log(`Errors: ${logs.filter(l => l.type === 'error').length}`);
    console.log(`Warnings: ${logs.filter(l => l.type === 'warning').length}`);

  } catch (error) {
    console.error('Failed to load page:', error.message);
  }

  await browser.close();
})();
