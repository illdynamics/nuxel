#!/usr/bin/env node
/*
 * Generate the canonical launcher icon registry from the two registries that
 * actually drive the UI:
 *
 *   - pwa/nuxel-home/js/apps.js        (NUXEL_APPS + NUXEL_APP_ICON_ASSETS)
 *   - pwa/nuxel-home/index.html        (navigation + Quick Settings artwork)
 *
 * and cross-check the canonical app registry's optional `icon_asset` fields.
 * The generated JSON is what the HTTP, WebKit and caching tests iterate; there
 * is no hand-maintained second list of icon URLs.
 *
 * Usage:
 *   node tools/s10plus/a44/generate-icon-registry.js            # write
 *   node tools/s10plus/a44/generate-icon-registry.js --check    # verify fresh
 *   node tools/s10plus/a44/generate-icon-registry.js --root DIR --check
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const zlib = require('zlib');

const HERE = __dirname;
const DEFAULT_ROOT = path.resolve(HERE, '..', '..', '..');
let root = DEFAULT_ROOT;
let check = false;
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === '--check') check = true;
  else if (process.argv[i] === '--root') root = path.resolve(process.argv[++i]);
  else if (process.argv[i] === '--help' || process.argv[i] === '-h') {
    console.log('usage: generate-icon-registry.js [--check] [--root DIR]'); process.exit(0);
  } else { console.error('unknown argument: ' + process.argv[i]); process.exit(2); }
}

const HOME = path.join(root, 'pwa/nuxel-home');
const APPS_JS = path.join(HOME, 'js/apps.js');
const INDEX = path.join(HOME, 'index.html');
const CANON = path.join(root, 'pwa/nuxel-common/app-registry.json');
const OUT = path.join(HOME, 'icon-registry.json');
const REVISION = 'a44';

function fail(message) { console.error('ICON-REGISTRY-FAIL: ' + message); process.exit(1); }
function sha256(data) { return crypto.createHash('sha256').update(data).digest('hex'); }
function fileSha(p) { return sha256(fs.readFileSync(p)); }
function rel(p) { return path.relative(root, p).split(path.sep).join('/'); }

function pngInfo(buf, source) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (buf.length < 33 || !buf.subarray(0, 8).equals(sig)) fail(source + ': not a PNG');
  let pos = 8, width = 0, height = 0, bitDepth = 0, colorType = -1, transparency = false;
  const idat = [];
  while (pos + 12 <= buf.length) {
    const len = buf.readUInt32BE(pos);
    const type = buf.toString('ascii', pos + 4, pos + 8);
    const body = buf.subarray(pos + 8, pos + 8 + len);
    if (pos + 12 + len > buf.length) fail(source + ': truncated PNG chunk ' + type);
    if (type === 'IHDR') {
      width = body.readUInt32BE(0); height = body.readUInt32BE(4);
      bitDepth = body[8]; colorType = body[9];
    } else if (type === 'tRNS') {
      transparency = true;
    } else if (type === 'IDAT') {
      idat.push(body);
    } else if (type === 'IEND') {
      break;
    }
    pos += 12 + len;
  }
  if (!width || !height) fail(source + ': PNG without IHDR dimensions');
  if (bitDepth !== 8 || (colorType !== 4 && colorType !== 6)) {
    fail(source + ': expected 8-bit RGBA/greyscale-alpha PNG, got bitDepth=' + bitDepth + ' colorType=' + colorType);
  }
  // Decode the alpha channel.  This is deliberately a real decode, not a
  // metadata-only claim: an RGBA header can still contain an all-opaque image.
  const bpp = 4;
  const stride = width * bpp;
  const raw = zlib.inflateSync(Buffer.concat(idat));
  if (raw.length < (stride + 1) * height) fail(source + ': short PNG image data');
  let prev = Buffer.alloc(stride);
  let transparent = 0, opaque = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    const row = Buffer.from(raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)));
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? row[x - bpp] : 0;
      const b = prev[x];
      const c = x >= bpp ? prev[x - bpp] : 0;
      let v = row[x];
      if (filter === 1) v = (v + a) & 255;
      else if (filter === 2) v = (v + b) & 255;
      else if (filter === 3) v = (v + Math.floor((a + b) / 2)) & 255;
      else if (filter === 4) {
        const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
        v = (v + (pa <= pb && pa <= pc ? a : (pb <= pc ? b : c))) & 255;
      } else if (filter !== 0) fail(source + ': unsupported PNG filter ' + filter);
      row[x] = v;
    }
    for (let x = 3; x < stride; x += bpp) {
      if (row[x] === 0) transparent++;
      else if (row[x] >= 240) opaque++;
    }
    prev = row;
  }
  if (!transparent) fail(source + ': RGBA image has no fully transparent pixels');
  if (!opaque) fail(source + ': RGBA image has no near-opaque artwork pixels');
  return { width, height, bitDepth, colorType, transparency: true,
           transparent_pixels: transparent, opaque_pixels: opaque };
}

function readApps() {
  const source = fs.readFileSync(APPS_JS, 'utf8');
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    window: {}, document: { addEventListener() {} },
    localStorage: { getItem() { return null; }, setItem() {} },
    CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
    setTimeout, clearTimeout,
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  try {
    vm.runInContext(source + '\nthis.__apps = NUXEL_APPS; this.__icons = NUXEL_APP_ICON_ASSETS;',
                    sandbox, { filename: APPS_JS });
  } catch (e) { fail('apps.js did not load: ' + e.message); }
  if (!sandbox.__apps || !sandbox.__icons) fail('apps.js is missing NUXEL_APPS or NUXEL_APP_ICON_ASSETS');
  return { apps: sandbox.__apps, icons: sandbox.__icons, source };
}

function addAsset(list, rec) {
  const url = String(rec.url || '');
  if (!url.startsWith('/assets/')) fail(rec.id + ': URL must be root-relative under /assets/, got ' + url);
  if (url.startsWith('/pwa/')) fail(rec.id + ': icon must not use the /pwa app tree: ' + url);
  const parsed = new URL('http://127.0.0.1:8000' + url);
  const urlPath = parsed.pathname;
  const sourceRel = urlPath.replace(/^\//, '');
  const source = path.join(root, sourceRel);
  if (!fs.existsSync(source) || !fs.statSync(source).isFile()) fail(rec.id + ': missing source ' + sourceRel);
  const data = fs.readFileSync(source);
  if (data.length < 128) fail(rec.id + ': implausibly small asset ' + sourceRel);
  const png = pngInfo(data, sourceRel);
  if (list.some(x => x.url === url)) fail('duplicate icon URL ' + url);
  list.push(Object.assign({}, rec, {
    url, path: urlPath, source: sourceRel, mime: 'image/png',
    bytes: data.length, sha256: sha256(data), width: png.width, height: png.height,
    bit_depth: png.bitDepth, color_type: png.colorType,
    transparent_pixels: png.transparent_pixels, opaque_pixels: png.opaque_pixels,
  }));
}

const appData = readApps();
const canonical = JSON.parse(fs.readFileSync(CANON, 'utf8'));
const canonById = new Map((canonical.apps || []).map(a => [a.id, a]));
const assets = [];

for (const [key, app] of Object.entries(appData.apps)) {
  const url = appData.icons[key];
  if (!url) fail('missing app icon registry entry for ' + key);
  const canon = canonById.get(app.id);
  if (!canon) fail('launcher app ' + app.id + ' is absent from ' + rel(CANON));
  if (!canon.icon_asset) fail('canonical registry entry ' + app.id + ' has no icon_asset');
  if (canon.icon_asset !== url) {
    fail('icon URL drift for ' + app.id + ': apps.js=' + url + ' canonical=' + canon.icon_asset);
  }
  addAsset(assets, { kind: 'app', id: app.id, app_id: app.id, registry: 'NUXEL_APP_ICON_ASSETS',
                     url, selector: '[data-app-id="' + app.id + '"] .app-icon img' });
}
for (const key of Object.keys(appData.icons)) {
  if (!appData.apps[key]) fail('orphan app icon registry entry ' + key);
}

const html = fs.readFileSync(INDEX, 'utf8');
const nav = [];
for (const m of html.matchAll(/<button\b[^>]*\bid="(nav-[^"]+)"[^>]*>([\s\S]*?)<\/button>/g)) {
  const img = /<img\b[^>]*\bsrc="([^"]+)"/.exec(m[2]);
  if (!img) fail(m[1] + ': navigation button has no image');
  nav.push({ id: m[1], button: m[1].replace(/^nav-/, ''), url: img[1],
             selector: '#' + m[1] + ' img' });
}
if (nav.length !== 3) fail('expected 3 navigation icons, found ' + nav.length);
for (const n of nav) addAsset(assets, { kind: 'navigation', id: n.id, button: n.button,
                                        selector: n.selector, url: n.url });

const toggles = [];
const nonImage = [];
for (const m of html.matchAll(/<div\b[^>]*class="qs-item"[^>]*\bid="(qs-[^"]+)"[^>]*>([\s\S]*?)<\/div>/g)) {
  const img = /<img\b[^>]*class="qs-icon"[^>]*\bsrc="([^"]+)"|<img\b[^>]*\bsrc="([^"]+)"[^>]*class="qs-icon"/.exec(m[2]);
  if (!img) { nonImage.push(m[1]); continue; }
  toggles.push({ id: m[1], toggle: m[1].replace(/^qs-/, ''), url: img[1] || img[2],
                 selector: '#' + m[1] + ' img.qs-icon' });
}
// The verbose-boot tile is a CSS glyph built by qs.js, not a custom raster.
const qsJs = fs.readFileSync(path.join(HOME, 'js/qs.js'), 'utf8');
if (!/id = 'qs-verbose-boot'/.test(qsJs)) {
  fail('qs.js no longer declares qs-verbose-boot; refresh the non-image toggle allow-list');
}
if (!nonImage.includes('qs-verbose-boot')) nonImage.push('qs-verbose-boot');
if (toggles.length !== 8) fail('expected 8 raster Quick Settings icons, found ' + toggles.length);
const unexpected = nonImage.filter(id => id !== 'qs-verbose-boot');
if (unexpected.length) fail('Quick Settings item(s) without a custom image and not allow-listed: ' + unexpected.join(', '));
for (const t of toggles) addAsset(assets, { kind: 'toggle', id: t.id, toggle: t.toggle,
                                            selector: t.selector, url: t.url });

const order = { app: 0, navigation: 1, toggle: 2 };
assets.sort((a, b) => (order[a.kind] - order[b.kind]) || a.id.localeCompare(b.id));
const counts = assets.reduce((o, a) => (o[a.kind] = (o[a.kind] || 0) + 1, o), {});
const output = {
  schema: 'nuxel.icon-registry/1',
  asset_revision: REVISION,
  generated_from: {
    canonical_app_registry: rel(CANON),
    canonical_app_registry_sha256: fileSha(CANON),
    launcher_registry: rel(APPS_JS),
    launcher_registry_sha256: fileSha(APPS_JS),
    launcher_html: rel(INDEX),
    launcher_html_sha256: fileSha(INDEX),
  },
  counts: { app: counts.app || 0, navigation: counts.navigation || 0, toggle: counts.toggle || 0,
            total: assets.length },
  non_image_toggles: nonImage.map(id => ({ id, reason: 'CSS-only control, no custom raster asset' })),
  assets,
};
const rendered = JSON.stringify(output, null, 2) + '\n';
if (check) {
  if (!fs.existsSync(OUT)) fail('missing generated registry ' + rel(OUT));
  if (fs.readFileSync(OUT, 'utf8') !== rendered) {
    fail(rel(OUT) + ' is stale; run: node tools/s10plus/a44/generate-icon-registry.js');
  }
  console.log('ICON-REGISTRY-OK ' + assets.length + ' assets (app=' + output.counts.app +
              ' navigation=' + output.counts.navigation + ' toggle=' + output.counts.toggle + ')');
} else {
  fs.writeFileSync(OUT, rendered);
  console.log('wrote ' + rel(OUT) + ': ' + assets.length + ' assets (app=' + output.counts.app +
              ' navigation=' + output.counts.navigation + ' toggle=' + output.counts.toggle + ')');
}
