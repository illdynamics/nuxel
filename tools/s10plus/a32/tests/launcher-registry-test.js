// Offline test: the authoritative app registry still contains the apps the A32
// features depend on, with the ids the docs and the button mapping use.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '../../../../pwa/nuxel-home/js/apps.js'), 'utf8');
const sandbox = { console: console, document: { addEventListener() {} }, window: {}, localStorage: { getItem: () => null, setItem() {} } };
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(src + '\nthis.__apps = NUXEL_APPS;', sandbox);
const apps = sandbox.__apps;
let failures = 0;
function check(n, c, x) { console.log((c ? 'PASS ' : 'FAIL ') + n + (c ? '' : '  ' + (x || ''))); if (!c) failures++; }
check('registry loaded', !!apps && Object.keys(apps).length >= 10, JSON.stringify(Object.keys(apps || {})));
for (const id of ['nuxel-settings', 'org.nuxel.Terminal', 'org.nuxel.Mail', 'org.nuxel.Calendar',
                  'org.nuxel.Notes', 'org.nuxel.Files', 'nuxel-camera', 'nuxel-dialer',
                  'nuxel-messages', 'nuxel-contacts']) {
  check('registry has ' + id, !!apps[id]);
}
check('settings is a served PWA, not the native placeholder',
      apps['nuxel-settings'].type === 'pwa' && /^\/pwa\/nuxel-apps\/settings\//.test(apps['nuxel-settings'].url),
      apps['nuxel-settings'].type + ' ' + apps['nuxel-settings'].url);
check('terminal is a served PWA under the authoritative tree',
      apps['org.nuxel.Terminal'].type === 'pwa' && /^\/pwa\/nuxel-apps\/terminal\//.test(apps['org.nuxel.Terminal'].url),
      apps['org.nuxel.Terminal'].url);
check('pwa urls all live under /pwa/nuxel-apps/',
      Object.values(apps).filter((a) => a.type === 'pwa').every((a) => a.url.startsWith('/pwa/nuxel-apps/')),
      JSON.stringify(Object.values(apps).filter((a) => a.type === 'pwa').map((a) => a.url)));
console.log(failures ? ('\n' + failures + ' FAILURES') : '\nregistry tests passed');
process.exit(failures ? 1 : 0);
