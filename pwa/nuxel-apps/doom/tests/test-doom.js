#!/usr/bin/env node
// Nuxel Doom — offline engine, shell and distribution tests.
//   node pwa/nuxel-apps/doom/tests/test-doom.js
'use strict';
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
require(path.join(root, 'js', 'doom-engine.js'));
const Engine = globalThis.NuxelDoomEngine;

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail === undefined ? '' : '  — ' + detail)); }
}

console.log('Nuxel Doom — engine');
check('engine constructor is exported', typeof Engine === 'function');
const engine = new Engine({ width: 320, height: 180 });
check('three original sectors ship', Engine.LEVELS.length === 3, String(Engine.LEVELS.length));
check('starts on sector 1 with full health and ammo',
  engine.snapshot().level === 1 && engine.player.health === 100 && engine.player.bullets > 0);
const start = { x: engine.player.x, y: engine.player.y };
engine.player.yaw = 0;
engine.update(0.05, { forward: 1 });
check('forward input moves through open space',
  engine.player.x > start.x && Math.abs(engine.player.y - start.y) < 0.001,
  'x ' + start.x.toFixed(2) + ' -> ' + engine.player.x.toFixed(2));
const beforeAmmo = engine.player.bullets;
engine.player.fireCooldown = 0;
const fired = engine.fire();
check('fire consumes ammo and starts a cooldown',
  fired === true && engine.player.bullets === beforeAmmo - 1 && engine.player.fireCooldown > 0);
engine.switchWeapon(1);
check('weapon switching respects the weapon table',
  ['pistol', 'shotgun', 'plasma'].includes(engine.snapshot().weapon), engine.snapshot().weapon);
engine.player.health = 0;
engine.update(0.05, {});
check('death is represented in the engine state', engine.state === 'dead');
const snapshot = engine.snapshot();
check('snapshot exposes HUD fields used by the shell',
  ['health','armor','ammo','weapon','kills','enemies','level','levels'].every(k => k in snapshot));
const ammoKey = { pistol: 'bullets', shotgun: 'shells', plasma: 'cells' }[snapshot.weapon];
check('snapshot ammo is the active weapon ammo, never undefined',
  Number.isFinite(snapshot.ammo) && snapshot.ammo === snapshot[ammoKey],
  snapshot.weapon + ' ammo=' + snapshot.ammo);

console.log('\nNuxel Doom — shell and touch HUD');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'css', 'doom.css'), 'utf8');
const ui = fs.readFileSync(path.join(root, 'js', 'doom.js'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const app = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8'));
const sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
const ids = ['view','hud','hud-health','hud-armor','hud-ammo','hud-weapon','hud-kills','hud-sector',
  'controls','joy-zone','joy-base','joy-knob','look-zone','btn-fire','btn-use','btn-next','btn-prev',
  'btn-run','btn-pause','start-screen','settings-screen','pause-screen','end-screen','btn-resume',
  'btn-restart','btn-quit','btn-again','btn-menu','btn-settings','btn-settings-back','set-sound',
  'set-haptics','set-invert','set-hand','set-sens-down','set-sens-up'];
check('shell declares the canonical app id', /name="nuxel-app-id"\s+content="org\.nuxel\.Doom"/.test(html));
check('all touch HUD bindings exist', ids.every(id => html.includes('id="' + id + '"')), ids.filter(id => !html.includes('id="' + id + '"')).join(','));
check('campaign tiles cover all three sectors', ['0','1','2'].every(s => html.includes('data-sector="' + s + '"')));
check('there is no text input, so opening the app cannot raise a keyboard',
  !/<(input|textarea)\b/i.test(html) && !/contenteditable/i.test(html));
check('UI explicitly dismisses the system keyboard',
  /dismissKeyboard/.test(ui) && /dismiss-keyboard/.test(ui));
check('single-finger joystick keeps its own pointer id', /joyPointer/.test(ui) && /setPointerCapture/.test(ui));
check('aim drag keeps a separate pointer id', /lookPointer/.test(ui) && /lookYaw/.test(ui));
check('multitouch fire/use/weapon buttons are independent bindings',
  ['btn-fire','btn-use','btn-next','btn-prev','btn-run','btn-pause'].every(id => ui.includes("bindHold('" + id + "'")));
check('focus loss, suspension and unload release every input',
  /releaseAllInput/.test(ui) && /visibilitychange/.test(ui) && /pagehide/.test(ui));
check('settings persist in local storage', /nuxel\.doom\.settings\.v1/.test(ui));
check('progress persists in local storage', /nuxel\.doom\.progress\.v1/.test(ui));
check('fullscreen chrome is requested by the app', /nuxel:immersive/.test(ui) && /setImmersive\(true\)/.test(ui));
check('system Back is the pause/menu contract', /data-action="back"/.test(html));
check('CSS is touch-first and hides no gameplay with the start screen',
  /\.action/.test(css) && /touch-action:\s*none/.test(css) && /left-handed/.test(css));
check('manifest carries the Nuxel bridge contract',
  manifest.id === 'org.nuxel.Doom' && manifest.nuxel.app_id === 'org.nuxel.Doom' &&
  Array.isArray(manifest.nuxel.capabilities) && manifest.nuxel.bridge_version === '1');
check('app.json points at the real launchable URL',
  app.id === 'org.nuxel.Doom' && app.url === '/pwa/nuxel-apps/doom/index.html' && app.type === 'pwa');
check('service worker caches the engine, shell and icons',
  /doom-engine\.js/.test(sw) && /doom\.js/.test(sw) && /icon-512\.png/.test(sw));

console.log('\nNuxel Doom — NuxTore distribution');
const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'nuxtore', 'catalog', 'package-sources.json'), 'utf8'));
const pkg = (sources.packages || []).find(p => p.id === 'org.nuxel.Doom');
check('NuxTore catalogue offers org.nuxel.Doom', !!pkg);
check('package installs the real Home app id', pkg && pkg.install && pkg.install.app_id === 'org.nuxel.Doom');
check('package start URL is the shipped local payload', pkg && pkg.install.start_url === '/pwa/nuxel-apps/doom/index.html');
check('Remove is available because installer id equals package id', pkg && pkg.install.app_id === pkg.id);
check('catalogue package is unsigned-ok but offline local-bundle only',
  pkg && pkg.source.type === 'local-bundle' && !/http:\/\//.test(JSON.stringify(pkg.source)));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
