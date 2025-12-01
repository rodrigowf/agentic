const puppeteer = require('puppeteer');

(async () => {
  const url = process.argv[2] || 'http://localhost:3000';
  const outputPath = process.argv[3] || '/home/rodrigo/agentic/debug/screenshots/mobile-default.png';
  const waitTime = parseInt(process.argv[4]) || 2000;

  console.log('📱 Taking mobile screenshot of: ' + url);
  console.log('⏳ Wait time: ' + waitTime + 'ms');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  
  await page.setViewport({
    width: 375,
    height: 812,
    isMobile: true,
    deviceScaleFactor: 2
  });

  await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForTimeout(waitTime);

  await page.screenshot({ path: outputPath, fullPage: true });
  
  console.log('✅ Screenshot saved to: ' + outputPath);
  console.log('📏 Viewport: 375x812 (mobile)');
  const title = await page.title();
  console.log('📄 Page title: ' + title);
  console.log('\n📋 File path for reference:');
  console.log(outputPath);

  await browser.close();
})();
