#!/usr/bin/env node
// Nuxel Doom — real WAD engine shell, touch mapping and NuTore distribution.
//   node pwa/nuxel-apps/doom/tests/test-doom.js
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const root = path.join(__dirname, '..');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail === undefined ? '' : '  — ' + detail)); }
}
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }

const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(root, 'css', 'doom.css'), 'utf8');
const ui = fs.readFileSync(path.join(root, 'js', 'doom.js'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const app = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8'));
const sw = fs.readFileSync(path.join(root, 'sw.js'), 'utf8');
const provenance = fs.readFileSync(path.join(root, 'engine', 'PROVENANCE.md'), 'utf8');
const jsFile = path.join(root, 'engine', 'websockets-doom.js');
const wasmFile = path.join(root, 'engine', 'websockets-doom.wasm');

console.log('Nuxel Doom — WAD engine');
check('vendored Chocolate Doom JS exists', fs.existsSync(jsFile));
check('vendored Chocolate Doom WASM exists', fs.existsSync(wasmFile));
check('engine JS hash matches provenance',
  provenance.includes(sha(jsFile)), sha(jsFile));
check('engine WASM hash matches provenance',
  provenance.includes(sha(wasmFile)), sha(wasmFile));
check('provenance pins the upstream source commit',
  /65e0d3ae2ffa604155eebd96ed40da6567bd08f4/.test(provenance));
check('GPL licence text ships with the engine',
  fs.existsSync(path.join(root, 'engine', 'COPYING.md')));
check('shell loads the WebAssembly engine, not the old raycaster',
  /websockets-doom\.js/.test(ui) && !/NuxelDoomEngine/.test(html) && !/doom-engine\.js/.test(html));
check('shell requests the real WAD catalogue from the bridge',
  /\/api\/v1\/doom\/wads/.test(ui) && /\/api\/v1\/doom\/wad\?id=/.test(ui));
check('WAD ids are digest-addressed, never raw paths in the URL',
  /encodeURIComponent\(wad\.id\)/.test(ui) && !/\/api\/v1\/doom\/wad\?path=/.test(ui));
check('IWAD and PWAD composition is supported', /-iwad/.test(ui) && /-file/.test(ui));
check('first map starts immediately for the PLAY path',
  /'-warp'/.test(ui) && /startMode === 'episode'/.test(ui));
check('engine is started with an explicit pin-free 320x200 canvas',
  /'-width', '320', '-height', '200'/.test(ui));

console.log('\nNuxel Doom — touch HUD');
const inputTags = html.match(/<(input|textarea)\b[^>]*>/gi) || [];
check('there is no text input, so opening the app cannot raise a keyboard',
  inputTags.every(tag => /type=["'](?:file|checkbox)["']/i.test(tag)) && !/contenteditable/i.test(html));
check('UI explicitly dismisses the system keyboard',
  /dismissKeyboard/.test(ui) && /dismiss-keyboard/.test(ui));
check('twin analog HUD ids exist', ['move-stick','aim-stick','move-knob','aim-knob','fire-left','fire-right','look-map']
  .every(id => html.includes('id="' + id + '"')));
check('old joystick/look/action cluster controls are removed',
  !/id="joy-zone"/.test(html) && !/id="look-zone"/.test(html) && !/id="look-left"/.test(html) &&
  !/id="look-right"/.test(html) && !/id="look-menu"/.test(html) && !/id="btn-fire"/.test(html) &&
  !/id="btn-use"/.test(html) && !/id="btn-next"/.test(html) && !/id="btn-prev"/.test(html) &&
  !/id="btn-run"/.test(html) && !/id="btn-pause"/.test(html));
check('both thumbsticks use the same class and CSS size variable',
  (html.match(/class="thumbstick"/g) || []).length === 2 && /--stick-size/.test(css) && /\.thumbstick \{/.test(css) && !/class="dpad/.test(html));
check('both fire buttons use the same class and sit below their own stick',
  (html.match(/class="fire-button"/g) || []).length === 2 &&
  html.indexOf('id="move-stick"') < html.indexOf('id="fire-left"') &&
  html.indexOf('id="aim-stick"') < html.indexOf('id="fire-right"'));
check('left analog stick maps to movement/strafe engine keys',
  /function applyMove/.test(ui) && /ArrowUp', 38/.test(ui) && /ArrowDown', 40/.test(ui) && /Comma', 188/.test(ui) && /Period', 190/.test(ui));
check('right analog stick maps to genuine turn keys with analog ramp', /function applyAim/.test(ui) && /aimPulse/.test(ui) && /ArrowLeft/.test(ui) && /ArrowRight/.test(ui) && /DEAD_ZONE/.test(ui));
check('two independent stick pointer owners and fire reference counting coexist', /bindStick\('move'\)/.test(ui) && /bindStick\('aim'\)/.test(ui) && /s\.pointer/.test(ui) && /function resetSticks/.test(ui));
check('both FIRE buttons share one reference-counted fire action',
  /bindHold\('fire-left', fireDown, fireUp\)/.test(ui) && /bindHold\('fire-right', fireDown, fireUp\)/.test(ui) &&
  /fireHoldCount/.test(ui) && /ControlLeft', 17/.test(ui));
check('MAP toggles the real engine automap key', /bindHold\('look-map'/.test(ui) && /function toggleMap/.test(ui) && /tapKey\('KeyM', 77/.test(ui) && /key_map_toggle 77/.test(ui));
check('engine config binds look-up/look-down scan codes', /key_lookup 73/.test(ui) && /key_lookdown 81/.test(ui));
check('focus loss, suspension and unload release every input',
  /releaseAllInput/.test(ui) && /visibilitychange/.test(ui) && /pagehide/.test(ui));
check('no stuck key survives pointer cancel/capture loss',
  /pointercancel/.test(ui) && /lostpointercapture/.test(ui) && /Array\.from\(held\.keys\(\)\)\.forEach\(keyUp\)/.test(ui));
check('settings persist in local storage', /nuxel\.doom\.wad\.settings\.v1/.test(ui));
check('selected WAD persists in local storage', /nuxel\.doom\.wad\.selected\.v1/.test(ui));
check('fullscreen chrome is requested by the app', /nuxel:immersive/.test(ui) && /setImmersive\(true\)/.test(ui));
check('system Back is the pause/menu contract', /window\.NuxelBack/.test(ui) && /pauseEngine\(\)/.test(ui));

console.log('\nNuxel Doom — engine comparison and distribution');
check('native Chocolate Doom comparison target is wired',
  /org\.nuxel\.Doom\.Chocolate/.test(ui));
check('removed comparison engines are not wired',
  !/org\.nuxel\.Doom\.UZDoom/.test(ui) && !/org\.nuxel\.Doom\.Crispy/.test(ui) && !/data-engine="uzdoom"/.test(html));
check('manifest is the 2.0 WAD-engine contract',
  manifest.id === 'org.nuxel.Doom' && manifest.version === '2.0.0' &&
  manifest.orientation === 'landscape' && Array.isArray(manifest.nuxel.capabilities));
check('app.json points at the real launchable URL',
  app.id === 'org.nuxel.Doom' && app.url === '/pwa/nuxel-apps/doom/index.html' && app.version === '2.0.0');
check('service worker caches the engine JS and WASM',
  /websockets-doom\.js/.test(sw) && /websockets-doom\.wasm/.test(sw) && /icon-512\.png/.test(sw));
const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'nuxtore', 'catalog', 'package-sources.json'), 'utf8'));
const pkg = (sources.packages || []).find(p => p.id === 'org.nuxel.Doom');
check('NuxTore catalogue offers org.nuxel.Doom 2.0.0', !!pkg && pkg.version === '2.0.0');
check('package installs the real Home app id', pkg && pkg.install && pkg.install.app_id === 'org.nuxel.Doom');
check('package start URL is the shipped local payload', pkg && pkg.install.start_url === '/pwa/nuxel-apps/doom/index.html');
check('Remove is available because installer id equals package id', pkg && pkg.install.app_id === pkg.id);
check('catalogue package is an offline local bundle',
  pkg && pkg.source.type === 'local-bundle' && !/http:\/\//.test(JSON.stringify(pkg.source)));
check('Chocolate Doom is not a standalone package/requirement',
  !(sources.packages || []).some(p => p.id === 'org.nuxel.Doom.Chocolate'));
check('UZDoom comparison package is gone',
  !(sources.packages || []).some(p => p.id === 'org.nuxel.Doom.UZDoom'));
check('Nuxel Doom declares its own bundled WASM engine and Freedoom runtime',
  pkg && Array.isArray(pkg.requires) && pkg.requires.some(r => /freedoom/i.test(r)) &&
  pkg.runtime && /WebAssembly/i.test(pkg.runtime.engine || ''));
check('Nuxel Doom reports required/default WAD fields without bundling commercial WADs',
  pkg && pkg.runtime && Array.isArray(pkg.runtime.default_wads) &&
  pkg.runtime.default_wads.includes('freedoom1.wad') &&
  pkg.wad_policy && pkg.wad_policy.commercial_wads_bundled === false);
check('WAD licensing document is shipped with the app',
  fs.existsSync(path.join(__dirname, '..', 'WAD-LICENSES.md')));

console.log('\nNuxel Doom — PWNAGE-88000 audio / controls / sensitivity');
check('engine argv never hard-codes -nomusic in the always-present list',
  /'-window', '-nogui', '-config', 'default.cfg'/.test(ui) && !/'-nogui', '-nomusic'/.test(ui));
check('explicit sound-off still disables sound and music',
  /!settings\.sound/.test(ui) && /'-nosound'/.test(ui) && /'-nomusic'/.test(ui));
check('audio unlocks from the first trusted Play gesture',
  /function primeAudio/.test(ui) && /AudioContext/.test(ui) && /audioUnlocked\(\)/.test(ui));
check('aim sensitivity defaults to 3 and is persisted',
  /sensitivity: 3/.test(ui) && /settings\.sensitivity/.test(ui) && /sens-down/.test(html) && /sens-up/.test(html));
check('sensitivity is a real multiplier on the aim duty cycle',
  /function aimDuty/.test(ui) && /Math\.abs\(magnitude\) \* sens/.test(ui));
check('Use/Map are top-left and −/+/Menu are top-right clusters',
  /top-cluster top-left/.test(html) && /top-cluster top-right/.test(html) &&
  html.indexOf('id="use-button"') < html.indexOf('id="look-map"') &&
  html.indexOf('id="weapon-prev"') < html.indexOf('id="weapon-next"') &&
  html.indexOf('id="weapon-next"') < html.indexOf('id="hud-menu"'));
check('USE maps to the engine Space key', /tapKey\('Space', 32/.test(ui));
check('weapon −/+ map to bracket scan codes', /tapKey\('BracketLeft', 219/.test(ui) && /tapKey\('BracketRight', 221/.test(ui));
check('MENU opens the engine pause menu (Escape), not only the app overlay',
  /tapKey\('Escape', 27/.test(ui) && /e\.code === 'Escape' && e\.isTrusted/.test(ui));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
