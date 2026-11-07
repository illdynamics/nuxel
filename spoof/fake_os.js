// win-spoof.js
const puppeteer = require('puppeteer-extra')
const stealth = require('puppeteer-extra-plugin-stealth')
puppeteer.use(stealth())

puppeteer.launch({ headless: false, args: ['--no-sandbox'] }).then(async browser => {
  const page = await browser.newPage()
  await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0")
  await page.goto("https://teams.microsoft.com")
})
