const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

puppeteer.use(StealthPlugin());

(async () => {
  const browser = await puppeteer.launch({
    headless: false,
    args: [
      '--use-fake-ui-for-media-stream', // Auto-accept cam/mic
      '--use-fake-device-for-media-stream',
      '--allow-file-access-from-files',
      '--enable-features=WebRTCPipeWireCapturer',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage'
    ]
  });

  const page = await browser.newPage();

  // 🔥 Realistic Windows+Edge User Agent
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0');

  // 🧠 Override navigator properties to spoof OS + GPU + media
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'platform', {
      get: () => 'Win32'
    });
    Object.defineProperty(navigator, 'oscpu', {
      get: () => 'Windows NT 10.0; Win64; x64'
    });
    Object.defineProperty(navigator, 'language', {
      get: () => 'en-US'
    });
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en']
    });

    // 🧠 Spoof WebGL fingerprint
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
      if (parameter === 37445) return 'NVIDIA Corporation'; // UNMASKED_VENDOR_WEBGL
      if (parameter === 37446) return 'NVIDIA GeForce RTX 3060/PCIe/SSE2'; // UNMASKED_RENDERER_WEBGL
      return getParameter.call(this, parameter);
    };

    // Spoof for WebGL2 too
    if (typeof WebGL2RenderingContext !== 'undefined') {
      const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
      WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'NVIDIA Corporation';
        if (parameter === 37446) return 'NVIDIA GeForce RTX 3060/PCIe/SSE2';
        return getParameter2.call(this, parameter);
      };
    }

    // 📸 Spoof mediaDevices for virtual cam
    Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
      value: async () => [{
        kind: 'videoinput',
        label: 'Integrated Camera',
        deviceId: 'wonk-cam-0',
        groupId: 'wonk-group-1'
      }]
    });
  });

  await page.goto('https://teams.microsoft.com');

  console.log('🔥 Spoofed Edge launched. Login manually if needed.');
})();
