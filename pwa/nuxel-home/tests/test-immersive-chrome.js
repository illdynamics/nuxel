#!/usr/bin/env node
// PWNAGE-76000 / v0.7.7-beta — immersive chrome contract.
//   node pwa/nuxel-home/tests/test-immersive-chrome.js
'use strict';
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'css', 'style.css'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');
const immersive = fs.readFileSync(path.join(root, 'js', 'immersive.js'), 'utf8');
const navdock = fs.readFileSync(path.join(root, '..', '..', 'tools', 's10plus', 'a45', 'nuxel-navdock.c'), 'utf8');
const statusbar = fs.readFileSync(path.join(root, '..', '..', 'tools', 's10plus', 'a45', 'nuxel-statusbar.c'), 'utf8');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail === undefined ? '' : '  — ' + detail)); }
}

console.log('Nuxel Home — immersive chrome');
check('index loads the immersive controller', /js\/immersive\.js/.test(html));
check('controller defines bottom/top edge bands', /BOTTOM_BAND/.test(immersive) && /TOP_BAND/.test(immersive));
check('bottom swipe reveals the triple buttons', /kind === 'nav' && dy < 0/.test(immersive) && /setNavVisible\(true\)/.test(immersive));
check('top pull reveals the status bar', /kind === 'status' && dy > 0/.test(immersive) && /setStatusVisible\(true\)/.test(immersive));
check('controller only runs for foreground apps', /ACTIVE.*LAUNCHING|state === 'ACTIVE'.*state === 'LAUNCHING'/s.test(immersive));
check('lockscreen is excluded', /locked\(\)/.test(immersive) && /lockscreen-active/.test(immersive));
check('same-origin iframe gets its own gesture listeners', /attach\(doc\)/.test(immersive) && /boundDocs/.test(immersive));
check('home notifies the native dock through the public API', /n\.setNavVisible/.test(immersive));
check('app-requested immersive mode is source-checked', /event\.source !== frame\.contentWindow/.test(immersive));
check('leaving an app/reset restores ordinary chrome', /resetChrome/.test(immersive) && /app-status-hidden/.test(immersive));
check('app.js attaches immersive gestures to each iframe', /NuxelImmersive\.attach\(doc\)/.test(app));
check('app.js hides the native dock for PWA foreground apps', /_setNavDock\(false\)/.test(app));
check('app.js restores the dock on Home/background', /_setNavDock\(true\)/.test(app));
check('app.js exposes setImmersive/dismissKeyboard/isLocked', /setImmersive\(on\)/.test(app) && /dismissKeyboard\(\)/.test(app) && /isLocked\(\)/.test(app));
check('CSS hides nav by default in app state', /body\.app-nav-hidden:not\(\.app-nav-revealed\) #system-navigation/.test(css));
check('CSS hides the top bar only in real immersive mode', /body\.app-status-hidden:not\(\.app-status-revealed\) #status-bar/.test(css));
check('immersive iframe fills the full display', /body\.app-immersive \.pwa-frame/.test(css) && /100dvh/.test(css));
check('lockscreen privacy rules win over app chrome', /lockscreen-active #system-navigation/.test(css) && /transform: none !important/.test(css));
check('a subtle bottom gesture affordance replaces the visible buttons', /body\.app-nav-hidden:not\(\.app-nav-revealed\)::after/.test(css));
check('no app can expose the nav while locked', /opacity: 0 !important/.test(css) && /pointer-events: none !important/.test(css));
check('Doom requests immersive mode', /nuxel:immersive/.test(fs.readFileSync(path.join(root, '..', 'nuxel-apps', 'doom', 'js', 'doom.js'), 'utf8')));
check('every foreground app is immersive by default (nav + top bar hidden)',
  /classList\.add\('app-nav-hidden', 'app-immersive', 'app-status-hidden'\)/.test(immersive));
check('global app chrome still requires an unlocked ACTIVE/LAUNCHING session',
  /if \(!allowed\(\)\) \{ resetChrome\(\); return; \}/.test(immersive));
check('leaving an app restores the native dock explicitly',
  /resetChrome\(\);\s*\n\s*const n = home\(\);\s*\n\s*if \(n && typeof n\.setNavVisible === 'function'\) n\.setNavVisible\(true\)/.test(immersive));
check('Home and lockscreen remain excluded by the allowed() gate',
  /function allowed\(\) \{ return activeState\(\) && !locked\(\); \}/.test(immersive));
check('app launch path dismisses the OSK explicitly', /this\._dismissKeyboard\(\)/.test(app));
check('boot forces portrait through the orientation owner', /_applyBootOrientation\(\)/.test(app) && /orientation', 'set', \{ mode: 'portrait' \}/.test(app));
check('boot portrait is held until a successful unlock', /_releaseBootOrientation\(\)/.test(app) && /_enterHomeAfterUnlock[\s\S]*?_releaseBootOrientation/.test(app));
check('release restores the mode selected before boot', /_bootOrientationPrevious/.test(app) && /mode: previous/.test(app) && /boot_previous_mode/.test(app));
check('warm launcher reload does not force a rotation', /nuxel-boot-locked/.test(app) && /if \(this\._isLocked\(\)/.test(app));
check('native apps hide the dock behind a gesture strip', /NAV_STRIP_HEIGHT/.test(navdock) && /dock_gesture_reveal/.test(navdock) && /strip_mode/.test(navdock));
check('the native strip refuses to map while locked', /NAV_DOCK_SHOW_REFUSED/.test(navdock) && /lock_state_read\(\) != 2/.test(navdock));
check('native app launch hides the layer-shell dock', /_launchNative[\s\S]*?_setNavDock\(false\)/.test(app));
check('native top bar defaults to a pull-down strip', /BAR_STRIP_HEIGHT/.test(statusbar) && /bar_reveal/.test(statusbar) && /strip_mode/.test(statusbar));
check('native top bar still refuses to paint while locked', /session_locked\(\)/.test(statusbar) && /bar_hide/.test(statusbar));
check('native strip expands on a downward swipe and auto-hides', /last_y - down_y/.test(statusbar) && /BAR_AUTOHIDE_MS/.test(statusbar));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
