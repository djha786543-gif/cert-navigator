const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    page.on('console', msg => {
        // ignore some network warnings
        if (msg.type() !== 'warning') {
            console.log('PAGE LOG:', msg.text());
        }
    });

    page.on('pageerror', error => {
        console.log('PAGE ERROR:', error.message);
    });

    page.on('requestfailed', request => {
        console.log('REQUEST FAILED:', request.url(), request.failure().errorText);
    });

    await page.goto('http://localhost:8080/index.html', { waitUntil: 'networkidle2' });
    await browser.close();
})();
