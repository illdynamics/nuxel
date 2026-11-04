#!/usr/bin/env node
// PWNAGE-76000 / v0.7.6-beta — immersive chrome contract.
//   node pwa/nuxel-home/tests/test-immersive-chrome.js
'use strict';
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'css', 'style.css'), 'utf8');
const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');
const immersive = fs.readFileSync(path.join(root, 'js', 'immersive.js'), 'utf8');

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

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
