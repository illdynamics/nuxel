/* Nuxel Electron identity spoof preload.
 *
 * Loaded by the bridge with NODE_OPTIONS=--require=... in the Electron main
 * process.  It applies a Windows user-agent and platform to every webContents
 * via the DevTools protocol (headers + pre-document JS) and keeps a portable
 * JS fallback for lookups the protocol does not cover.  The Flatpak/bwrap
 * sandbox remains authoritative.
 */
'use strict';

let electron;
try {
  electron = require('electron');
} catch (err) {
  console.error('[nuxel-spoof] electron unavailable:', err && err.message);
  module.exports = {};
  return;
}

const UA = process.env.NUXEL_SPOOF_UA ||
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0';
const PLATFORM = process.env.NUXEL_SPOOF_PLATFORM || 'Win32';
const BRANDS = [
  { brand: 'Not?A_Brand', version: '24' },
  { brand: 'Chromium', version: '152' },
  { brand: 'Microsoft Edge', version: '152' },
];
const FULL_VERSION = '152.0.7977.167';
const SCRIPT = `(() => {
  const ua = ${JSON.stringify(UA)};
  const brands = ${JSON.stringify(BRANDS)};
  const uad = {brands: brands, mobile: false, platform: 'Windows'};
  const def = (obj, prop, val) => { try { Object.defineProperty(obj, prop, {get: () => val, configurable: true}); } catch (e) {} };
  def(Navigator.prototype, 'userAgent', ua);
  def(Navigator.prototype, 'appVersion', ua.replace('Mozilla/', ''));
  def(Navigator.prototype, 'platform', ${JSON.stringify(PLATFORM)});
  def(Navigator.prototype, 'oscpu', 'Windows NT 10.0; Win64; x64');
  def(Navigator.prototype, 'userAgentData', uad);
  try { def(navigator, 'userAgent', ua); } catch (e) {}
  try { def(navigator, 'platform', ${JSON.stringify(PLATFORM)}); } catch (e) {}
  try { def(navigator, 'userAgentData', uad); } catch (e) {}
  try {
    NavigatorUAData.prototype.getHighEntropyValues = async () => ({
      platform: 'Windows', platformVersion: '10.0.0', architecture: 'x86', model: '',
      uaFullVersion: ${JSON.stringify(FULL_VERSION)}, fullVersionList: brands,
      bitness: '64', wow64: false, mobile: false
    });
  } catch (e) {}
  try { def(Navigator.prototype, 'maxTouchPoints', 0); } catch (e) {}
  try { def(Navigator.prototype, 'language', 'en-US'); } catch (e) {}
  try { def(Navigator.prototype, 'languages', ['en-US', 'en']); } catch (e) {}
  window.__nuxelSpoof = {ua: ua, platform: ${JSON.stringify(PLATFORM)}};
})();`;

const attached = new WeakSet();

function metadata() {
  return {
    brands: BRANDS,
    fullVersion: FULL_VERSION,
    fullVersionList: BRANDS.map((b) => ({ brand: b.brand, version: FULL_VERSION })),
    platform: 'Windows',
    platformVersion: '10.0.0',
    architecture: 'x86',
    model: '',
    mobile: false,
    bitness: '64',
    wow64: false,
  };
}

function applyToWebContents(wc) {
  if (!wc || typeof wc.setUserAgent !== 'function') return;
  try { wc.setUserAgent(UA); } catch (e) {}
  try {
    if (!wc.debugger.isAttached()) wc.debugger.attach('1.3');
    const dbg = wc.debugger;
    dbg.sendCommand('Network.enable').catch(() => {});
    dbg.sendCommand('Network.setUserAgentOverride', {
      userAgent: UA,
      acceptLanguage: 'en-US,en;q=0.9',
      platform: PLATFORM,
      userAgentMetadata: metadata(),
    }).catch(() => {});
    dbg.sendCommand('Page.enable').catch(() => {});
    if (!attached.has(wc)) {
      attached.add(wc);
      dbg.sendCommand('Page.addScriptToEvaluateOnNewDocument', { source: SCRIPT })
        .catch(() => {});
    }
  } catch (err) {
    console.error('[nuxel-spoof] debugger attach failed:', err && err.message);
  }
  try { wc.executeJavaScript(SCRIPT, true).catch(() => {}); } catch (e) {}
  wc.on('did-start-navigation', () => {
    try { wc.setUserAgent(UA); } catch (e) {}
    applyToWebContents(wc);
  });
  wc.on('dom-ready', () => {
    try { wc.setUserAgent(UA); } catch (e) {}
    try { wc.executeJavaScript(SCRIPT, true).catch(() => {}); } catch (e) {}
  });
}

try {
  electron.app.on('web-contents-created', (_event, wc) => applyToWebContents(wc));
  const ready = () => {
    try {
      const ses = electron.session.defaultSession;
      if (ses) {
        ses.setUserAgent(UA);
        ses.webRequest.onBeforeSendHeaders({ urls: ['*://*/*'] }, (details, callback) => {
          const headers = details.requestHeaders || {};
          headers['User-Agent'] = UA;
          headers['Sec-CH-UA-Platform'] = '"Windows"';
          callback({ requestHeaders: headers });
        });
      }
    } catch (err) {
      console.error('[nuxel-spoof] session hook failed:', err && err.message);
    }
    try {
      for (const wc of electron.webContents.getAllWebContents()) applyToWebContents(wc);
    } catch (err) {
      console.error('[nuxel-spoof] existing webContents failed:', err && err.message);
    }
    console.error('[nuxel-spoof] Windows identity active');
  };
  if (electron.app.isReady()) ready();
  else electron.app.whenReady().then(ready);
} catch (err) {
  console.error('[nuxel-spoof] init failed:', err && err.message);
}
