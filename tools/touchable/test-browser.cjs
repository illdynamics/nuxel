// Real WebKit rendering and browser-delivered input. This is synthetic coverage,
// never physical owner acceptance. Install Playwright in build/touchable/browser.
const { webkit } = require('../../build/touchable/browser/node_modules/playwright');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const out = path.join(root, 'docs/touchable/evidence/browser-tests');
fs.mkdirSync(out, { recursive: true });
const types = { '.js': 'application/javascript', '.css': 'text/css', '.html': 'text/html', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
    let file = path.join(root, decodeURIComponent(new URL(req.url, 'http://localhost').pathname));
    if (!file.startsWith(root + '/')) { res.writeHead(403); return res.end(); }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    fs.readFile(file, (error, data) => {
        if (error) { res.writeHead(404); return res.end(); }
        res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
        res.end(data);
    });
});
(async () => {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const browser = await webkit.launch();
    const page = await browser.newPage({ viewport: { width: 360, height: 760 }, deviceScaleFactor: 2, hasTouch: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    try {
        // This test has no phone HTTP backend. Use a same-origin unavailable
        // endpoint so the existing offline fallback is exercised without
        // WebKit turning cross-origin transport diagnostics into page errors.
        await page.addInitScript(() => { window.NUXEL_API_URL = location.origin + '/test-backend-unavailable'; });
        await page.goto(`http://127.0.0.1:${server.address().port}/pwa/nuxel-home/index.html?boot=os`);
        await page.waitForFunction(() => window.nuxel && window.launcher);
        await page.evaluate(() => {
            window.__launches = [];
            document.addEventListener('app:launch', e => window.__launches.push(e.detail.app.id));
        });
        const before = await page.screenshot();
        for (const id of ['nuxel-settings', 'org.nuxel.Calendar', 'nuxel-settings', 'org.nuxel.Notes', 'nuxel-settings']) {
            await page.locator(`.app-item[data-app-id="${id}"]`).tap();
            await page.waitForFunction(id => window.nuxel.appSession.state === 'ACTIVE' && window.nuxel.appSession.app.id === id, id);
            assert.equal(await page.locator('.pwa-frame').count(), 1);
            const home = page.locator('.pwa-close-btn');
            assert.equal(await home.isVisible(), true);
            const box = await home.boundingBox();
            assert(box.y >= 36 && box.x < 100, 'Home clear of camera and app controls');
            const rendered = await page.screenshot();
            assert(!before.equals(rendered), 'app changes rendered pixels');
            await home.tap();
            assert.equal(await page.locator('.pwa-frame, .pwa-app-bar, .pwa-app-status').count(), 0);
            assert.equal(await page.evaluate(() => window.nuxel.appSession.state), 'CLOSED');
            console.log('PASS WebKit tap / active app / visible Home / cleanup: ' + id);
        }
        assert.equal(await page.evaluate(() => window.__launches.length), 5);
        await page.locator('.app-item[data-app-id="nuxel-settings"]').focus();
        await page.keyboard.press('Enter');
        await page.waitForFunction(() => window.nuxel.appSession.state === 'ACTIVE');
        await page.screenshot({ path: path.join(out, 'settings.png') });
        await page.locator('.pwa-close-btn').tap();
        await page.screenshot({ path: path.join(out, 'home.png') });
        assert.deepEqual(errors, [], 'no uncaught JavaScript errors');
        console.log('PASS browser keyboard activation and no JS exceptions');
    } finally {
        fs.writeFileSync(path.join(out, 'errors.json'), JSON.stringify(errors, null, 2) + '\n');
        await browser.close(); server.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; server.close(); });
