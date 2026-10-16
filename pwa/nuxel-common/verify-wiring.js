#!/usr/bin/env node
/**
 * Nuxel PWA bridge wiring verifier (CI assertion).
 *
 * Verifies that every PWA surface (nuxel-home + the 5 nuxel-apps) resolves the
 * SHARED bridge client from pwa/nuxel-common/bridge.js as an ES module, carries
 * the required `<meta name="nuxel-app-id">` tag, and does NOT vendor an inline
 * duplicate copy of the bridge implementation.
 *
 * Usage:
 *     node pwa/nuxel-common/verify-wiring.js      # from repo root
 *     node verify-wiring.js                       # from pwa/nuxel-common
 *
 * Exits non-zero (fails CI) if any assertion is violated.
 */
import { createRequire } from 'node:module';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve, relative, sep } from 'node:path';

const require = createRequire(import.meta.url);

// Resolve the workspace-rooted PWA directory regardless of cwd.
const here = dirname(fileURLToPath(import.meta.url)); // .../pwa/nuxel-common
const pwaRoot = resolve(here, '..');

const SHARED_BRIDGE_REL = 'nuxel-common/bridge.js';
const SHARED_BRIDGE_ABS = resolve(pwaRoot, SHARED_BRIDGE_REL);

// app id -> path (relative to pwaRoot)
const PWAS = {
    'org.nuxel.Home': 'nuxel-home/index.html',
    'org.nuxel.Calendar': 'nuxel-apps/calendar/index.html',
    'org.nuxel.Camera': 'nuxel-apps/camera-gallery/index.html',
    'org.nuxel.Files': 'nuxel-apps/files/index.html',
    'org.nuxel.Mail': 'nuxel-apps/mail/index.html',
    'org.nuxel.Notes': 'nuxel-apps/notes/index.html',
};

// System surfaces are not third-party apps: the launcher manifest may declare
// the HOST implementation version instead of the protocol pin, and that is
// reported as a note rather than failing the wiring check.
const SYSTEM_SURFACES = new Set(['org.nuxel.Home']);

// The pinned PWA<->host protocol version (briq-04c). Every app manifest must
// declare `nuxel.bridge_version` equal to it, or the host refuses the app.
const VERSION_PIN_PATH = resolve(pwaRoot, 'nuxel-common/bridge-version.json');

// Marker patterns for a *vendored duplicate* of the bridge. The shared bridge
// is the only file allowed to define the class or the token-resolution logic.
const DUPLICATE_MARKERS = [
    /\bclass\s+NuxelBridgeClient\b/,
    /\bclass\s+NuxelBridgeClientClient\b/,
    /NuxelBridgeClient\s*=\s*class/,
    /_mockCall\s*\(/,
    /MOCK_STORE\b/,
    /localStorage\.getItem\s*\(\s*['"]nuxel-bridge-token['"]\s*\)/,
    /window\.__NUXEL_TOKEN__/,
];

function collectJsFiles(dir, out = []) {
    if (!existsSync(dir)) return out;
    for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) {
            // skip standard node/ignored dirs
            if (['node_modules', '.git'].includes(entry)) continue;
            collectJsFiles(full, out);
        } else if (entry.endsWith('.js') || entry.endsWith('.mjs') || entry.endsWith('.cjs')) {
            out.push(full);
        }
    }
    return out;
}

let failures = 0;
const fail = (msg) => { failures += 1; console.error('  ✗ ' + msg); };
const pass = (msg) => console.log('  ✓ ' + msg);

console.log(`[verify-wiring] shared bridge: ${SHARED_BRIDGE_REL} => ${SHARED_BRIDGE_ABS}`);
console.log(`[verify-wiring] scanning ${Object.keys(PWAS).length} PWA surfaces\n`);

if (!existsSync(SHARED_BRIDGE_ABS)) {
    console.error(`FATAL: shared bridge module missing: ${SHARED_BRIDGE_ABS}`);
    process.exit(1);
}

let versionPin = null;
if (existsSync(VERSION_PIN_PATH)) {
    try {
        versionPin = JSON.parse(readFileSync(VERSION_PIN_PATH, 'utf8')).bridge_version;
    } catch (e) {
        console.error(`FATAL: ${VERSION_PIN_PATH} is not valid JSON: ${e.message}`);
        process.exit(1);
    }
} else {
    console.error(`FATAL: bridge version pin missing: ${VERSION_PIN_PATH}`);
    process.exit(1);
}
console.log(`[verify-wiring] pinned bridge_version = ${versionPin} (${relative(pwaRoot, VERSION_PIN_PATH)})\n`);

for (const [appId, relHtml] of Object.entries(PWAS)) {
    const absHtml = resolve(pwaRoot, relHtml);
    const label = relHtml.split(sep).slice(0, -1).join(sep) || relHtml;
    if (!existsSync(absHtml)) {
        console.error(`[verify-wiring] MISSING index.html: ${absHtml}`);
        process.exit(1);
    }
    const html = readFileSync(absHtml, 'utf8');
    console.log(`── ${appId} (${label})`);

    // 1. meta nuxel-app-id present and correct.
    const metaRe = /<meta\s+name=["']nuxel-app-id["']\s+content=["']([^"']+)["']\s*>/i;
    const metaMatch = html.match(metaRe);
    if (!metaMatch) {
        fail(`missing <meta name="nuxel-app-id">`);
    } else if (metaMatch[1] !== appId) {
        fail(`meta nuxel-app-id "${metaMatch[1]}" != expected "${appId}"`);
    } else {
        pass(`nuxel-app-id meta = ${metaMatch[1]}`);
    }

    // 2. bridge.js loaded as an ES module from the shared nuxel-common path.
    const scriptRe = /<script\s+[^>]*?type=["']module["'][^>]*src=["']([^"']+)["'][^>]*>/gi;
    let moduleScripts = [];
    let m;
    while ((m = scriptRe.exec(html)) !== null) moduleScripts.push(m[1]);

    const bridgeModules = moduleScripts.filter((src) => src && src.includes('bridge.js'));
    if (bridgeModules.length === 0) {
        fail('no ES-module <script type="module"> referencing bridge.js');
    } else if (bridgeModules.length > 1) {
        fail(`multiple bridge module includes: ${bridgeModules.join(', ')}`);
    } else {
        const src = bridgeModules[0];
        const resolved = resolve(dirname(absHtml), src);
        // Normalize path separators on all platforms to a slash form.
        const norm = (p) => p.split(sep).join('/');
        const isShared =
            norm(resolved) === norm(SHARED_BRIDGE_ABS) &&
            norm(src).indexOf('nuxel-common/bridge.js') !== -1;
        // Reject the case where a PWA re-hosted a copy (e.g. into js/bridge.js).
        const looksLocalCopy = !norm(src).includes('nuxel-common/bridge.js');
        if (!isShared) {
            fail(`bridge.js not resolved from nuxel-common: src="${src}" resolves to ${resolved}`);
        } else if (looksLocalCopy) {
            fail(`bridge.js appears vendored locally (not from nuxel-common): ${src}`);
        } else {
            pass(`bridge.js loaded as shared ES module: ${src} -> nuxel-common/bridge.js`);
        }
    }

    // 3. Reject inline / vendored duplicates of the bridge implementation.
    const jsDir = resolve(dirname(absHtml), 'js');
    const dupFiles = [];
    for (const jsFile of collectJsFiles(jsDir)) {
        const body = readFileSync(jsFile, 'utf8');
        for (const marker of DUPLICATE_MARKERS) {
            if (marker.test(body)) {
                dupFiles.push(`${relative(pwaRoot, jsFile)} (marker: ${marker})`);
                break;
            }
        }
    }
    if (dupFiles.length > 0) {
        fail(`inline/vendored bridge duplicates found:\n        ${dupFiles.join('\n        ')}`);
    } else {
        pass('no inline/vendored bridge duplicate in local js/');
    }

    // 4. The app manifest must declare the pinned protocol version.
    const manifestPath = resolve(dirname(absHtml), 'manifest.json');
    if (!existsSync(manifestPath)) {
        fail(`no manifest.json next to ${relHtml}`);
    } else {
        let mf = null;
        try {
            mf = JSON.parse(readFileSync(manifestPath, 'utf8'));
        } catch (e) {
            fail(`manifest.json is not valid JSON: ${e.message}`);
        }
        if (mf) {
            const declared = mf.nuxel && mf.nuxel.bridge_version;
            if (SYSTEM_SURFACES.has(appId)) {
                console.log(`  i  ${appId} is a system surface; manifest declares bridge_version=${JSON.stringify(declared)} (pin is ${versionPin})`);
            } else if (declared !== versionPin) {
                fail(`manifest nuxel.bridge_version is ${JSON.stringify(declared)}, expected the pin ${JSON.stringify(versionPin)}`);
            } else {
                pass(`manifest nuxel.bridge_version = ${declared} (matches the pin)`);
            }
            if (!SYSTEM_SURFACES.has(appId) && !(mf.nuxel && Array.isArray(mf.nuxel.capabilities))) {
                fail('manifest has no nuxel.capabilities list');
            }
        }
    }
    console.log('');
}

if (failures === 0) {
    console.log('[verify-wiring] ALL 6 PWA SURFACES OK');
    process.exit(0);
}
console.error(`[verify-wiring] ${failures} assertion(s) FAILED`);
process.exit(1);
