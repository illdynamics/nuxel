/* Nuxel patched PlatformEmulator for teams-for-linux.
 *
 * Upstream 2.28.0 calls structuredClone(navigator.userAgentData), which throws
 * ("NavigatorUAData object could not be cloned").  The exception aborts the
 * whole module after navigator.platform has been overwritten, leaving
 * navigator.userAgentData.platform and the UA-CH brands reporting Linux.
 * That is exactly the signal AAD/Teams uses to decide this is a Linux device.
 *
 * This version builds a normal JS object instead, reports Windows + the Edge
 * brand set, and additionally repairs the AAD converged-login pagination state
 * that otherwise leaves the "Switch Edge profile" / "Trying to sign you in"
 * progress view on screen forever in Electron.
 */
'use strict';

const chromeVersion = (process.versions && process.versions.chrome) || '152.0.7977.167';
const major = String(chromeVersion).split('.')[0] || '152';
const FULL_VERSION = chromeVersion;

const isEdge = /\bEdg\//i.test(navigator.userAgent || '');
const primaryBrand = isEdge ? 'Microsoft Edge' : 'Google Chrome';
const BRANDS = [
  { brand: primaryBrand, version: major },
  { brand: 'Chromium', version: major },
  { brand: 'Not_A Brand', version: '24' },
];
const FULL_VERSION_LIST = [
  { brand: primaryBrand, version: FULL_VERSION },
  { brand: 'Chromium', version: FULL_VERSION },
  { brand: 'Not_A Brand', version: '24.0.0.0' },
];

function define(obj, prop, value) {
  try {
    Object.defineProperty(obj, prop, { get: () => value, configurable: true });
  } catch (e) {}
}

function installAadPaginationFix() {
  if (!/^login\.microsoftonline\.com$/i.test(window.location.hostname) &&
      !/^login\.microsoft\.com$/i.test(window.location.hostname)) {
    return;
  }
  let lastSwitch = 0;
  const tick = () => {
    try {
      const viewEl = document.querySelector('[data-viewid]');
      if (!viewEl || !window.ko) return;
      const pc = window.ko.dataFor(viewEl);
      if (!pc) return;
      const cur = pc.getCurrentViewId ? pc.getCurrentViewId() : null;
      // FetchSessionsProgress (55) is the desktop-SSO/BSSO spinner.  In
      // Electron there is no Edge/WAM broker, so it never completes.  Switch
      // to the normal username view and drive the broken CSS animation state.
      if (cur === 55 && document.getElementById('desktopSsoCancel') &&
          Date.now() - lastSwitch > 4000) {
        lastSwitch = Date.now();
        pc.view_onSwitchView(1, true, true);
        let i = 0;
        const pump = () => {
          try { pc.view_onAnimationEnd(); } catch (e) {}
          if (++i < 14) setTimeout(pump, 90);
        };
        pump();
      }
      // The pagination component sometimes leaves the selected view hidden or
      // collapsed (height 0) in the middle of a CSS transition: the SAS
      // number-matching / password / OTC pages are rendered but invisible.
      // Drive the animation state machine to completion.
      const rect = viewEl.getBoundingClientRect();
      const hidden = pc.hidePaginatedView && pc.hidePaginatedView() === true;
      const collapsed = rect.height === 0 && cur !== null;
      if (hidden || collapsed) {
        if (hidden) {
          pc.hidePaginatedView(false);
          if (pc.hidePaginatedView.hideSubView) pc.hidePaginatedView.hideSubView(false);
        }
        if (pc.animate && pc.animate() !== 'None') pc.animate('None');
        if (pc.view_onAnimationEnd) {
          let n = 0;
          const pump = () => {
            try { pc.view_onAnimationEnd(); } catch (e) {}
            if (++n < 6) setTimeout(pump, 90);
          };
          pump();
        }
      }
    } catch (e) {}
  };
  setInterval(tick, 1000);
  setTimeout(tick, 0);
}

class PlatformEmulator {
  init(config) {
    if (!config.emulateWinChromiumPlatform) return;

    define(Navigator.prototype, 'platform', 'Win32');

    const uaData = {
      brands: BRANDS,
      mobile: false,
      platform: 'Windows',
      getHighEntropyValues: async (hints) => {
        const out = {
          brands: BRANDS,
          mobile: false,
          platform: 'Windows',
        };
        hints = Array.isArray(hints) ? hints : [];
        if (hints.includes('platformVersion')) out.platformVersion = '10.0.0';
        if (hints.includes('architecture')) out.architecture = 'x86';
        if (hints.includes('bitness')) out.bitness = '64';
        if (hints.includes('model')) out.model = '';
        if (hints.includes('uaFullVersion')) out.uaFullVersion = FULL_VERSION;
        if (hints.includes('fullVersionList')) out.fullVersionList = FULL_VERSION_LIST;
        if (hints.includes('wow64')) out.wow64 = false;
        return out;
      },
      toJSON: () => ({ brands: BRANDS, mobile: false, platform: 'Windows' }),
    };
    define(Navigator.prototype, 'userAgentData', uaData);
    try { define(navigator, 'userAgentData', uaData); } catch (e) {}

    installAadPaginationFix();
  }
}

module.exports = new PlatformEmulator();
