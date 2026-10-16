/**
 * Nuxel common bridge — node-runnable test harness (ESM).
 *
 * Usage:
 *     cd pwa/nuxel-common && npm test
 *     node pwa/nuxel-common/test-bridge.js
 *
 * Starts a mock HTTP server that simulates the real nuxel-bridge endpoints
 * (/ping, /auth/token, /rpc) and exercises the shared bridge client
 * end-to-end: token bootstrap, token-header validation, generic RPC calls,
 * the window-token source, and mock fallback when the server is unreachable.
 */

import { createServer } from 'node:http';
import assert from 'node:assert';
import { NuxelBridgeClient, NUXEL_BRIDGE_VERSION, NuxelBridgeVersionError } from './bridge.js';

// The /ping response's bridge_version. undefined => the pinned value (healthy
// host); null => a legacy host that declares nothing; a string => a skewed host.
let VERSION_OVERRIDE;

// ---- Mock nuxel-bridge HTTP server --------------------------------
const authenticatedTokens = new Set();
const server = createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    const send = (code, body) => { res.statusCode = code; res.end(JSON.stringify(body)); };

    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
        let payload = {};
        try { payload = body ? JSON.parse(body) : {}; } catch (e) {}

        const path = req.url.split('?')[0];

        // Bootstrap: no auth required.
        if (path === '/api/v1/auth/token' && req.method === 'POST') {
            const token = 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2);
            authenticatedTokens.add(token);
            return send(200, { success: true, token, ttl: 3600, expires_at: Date.now() + 3600e3 });
        }

        // All other endpoints require a valid per-session token.
        const auth = req.headers.authorization || '';
        if (!auth.startsWith('Bearer ') || !authenticatedTokens.has(auth.slice(7))) {
            return send(401, { error: 'Unauthorized' });
        }

        if (path === '/api/v1/ping' && req.method === 'GET') {
            const proto = VERSION_OVERRIDE === undefined ? NUXEL_BRIDGE_VERSION : VERSION_OVERRIDE;
            const body = { status: 'ok', version: '0.4.0-alpha' };
            if (proto !== null) body.bridge_version = proto;
            return send(200, body);
        }

        // Generic RPC.
        if (path === '/api/v1/rpc' && req.method === 'POST') {
            const { namespace, verb } = payload;
            if (namespace === 'storage' && verb === 'list-dir') {
                return send(200, { result: { success: true, entries: [{ name: 'readme.txt', path: '/readme.txt' }] } });
            }
            if (namespace === 'mail' && verb === 'imap-list') {
                return send(200, { result: { success: true, messages: [{ id: '1', subject: 'Hello' }] } });
            }
            if (namespace === 'camera' && verb === 'list-captures') {
                return send(200, { result: { success: true, captures: [] } });
            }
            return send(200, { result: { success: true } });
        }

        return send(404, { error: 'Not found' });
    });
});

// Use an OS-assigned ephemeral port so the test never conflicts with other
// local services (avoid EADDRINUSE). `server.listen(0)` lets the OS pick one.
const requestedPort = 0; // 0 => OS-assigned ephemeral port
let PORT;
const base = () => `http://127.0.0.1:${PORT}/api/v1`;

async function main() {
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(requestedPort, '127.0.0.1', resolve);
    });
    PORT = server.address().port;
    const uri = base();
    console.log('[test] mock bridge listening on ' + uri);

    // Route the module's bare `fetch(...)` calls (and any relative or absolute
    // URLs) to the mock server by overriding the global fetch.
    const origFetch = globalThis.fetch;
    globalThis.fetch = (url, opts) => {
        const u = String(url).startsWith('http') ? url : base() + String(url);
        return origFetch(u, opts);
    };

    // 1. Connected + ping via bootstrapped per-session token.
    const client = new NuxelBridgeClient({ apiUrl: base(), appId: 'org.nuxel.Test' });
    await client._init();
    assert.strictEqual(client.connected, true, 'bridge should be connected');
    assert.ok(client.token, 'a per-session token should have been bootstrapped');

    // 2. Generic RPC call returns the result payload.
    const listing = await client.call('storage', 'list-dir', { path: '/' });
    assert.strictEqual(listing.success, true);
    assert.ok(Array.isArray(listing.entries), 'list-dir returns entries array');
    assert.strictEqual(listing.entries.length, 1);
    console.log('[test] rpc storage.list-dir ok:', listing.entries.length, 'entry');

    const mail = await client.call('mail', 'imap-list', { account: 'a', folder: 'INBOX' });
    assert.ok(Array.isArray(mail.messages), 'imap-list returns messages');
    assert.strictEqual(mail.messages.length, 1);
    console.log('[test] rpc mail.imap-list ok:', mail.messages.length, 'message');

    // 3. Token source precedence: window.__NUXEL_TOKEN__ wins.
    globalThis.window = globalThis;
    globalThis.__NUXEL_TOKEN__ = 'from-window-token';
    const c2 = new NuxelBridgeClient({ apiUrl: base(), appId: 'org.nuxel.Test2' });
    await c2._resolveToken();
    assert.strictEqual(c2.token, 'from-window-token', 'window token should be preferred');
    console.log('[test] token from window.__NUXEL_TOKEN__ ok');

    // 4. Mock fallback when the server is unreachable.
    await new Promise((r) => server.close(r));
    const c3 = new NuxelBridgeClient({ apiUrl: 'http://127.0.0.1:1', appId: 'org.nuxel.Offline' });
    const fallback = await c3.call('storage', 'list-dir', { path: '/offline' });
    assert.strictEqual(c3.mockMode, true, 'should fall back to mock mode');
    assert.strictEqual(fallback.success, true, 'mock fallback returns success');
    assert.strictEqual(fallback.mock, true, 'mock fallback flagged');
    console.log('[test] mock fallback ok');

    // 5. Pin integrity: the compiled-in literal is the protocol contract and the
    //    manifest helper agrees with it.
    assert.strictEqual(NUXEL_BRIDGE_VERSION, '1', 'pinned bridge_version');
    assert.deepStrictEqual(
        NuxelBridgeClient.checkManifest({ nuxel: { bridge_version: '1' } }),
        { compatible: true, declared: '1', expected: '1' });
    assert.strictEqual(
        NuxelBridgeClient.checkManifest({ nuxel: { bridge_version: '2' } }).compatible, false,
        'a manifest pinned to another protocol version is incompatible');
    assert.strictEqual(
        NuxelBridgeClient.checkManifest({}).compatible, false,
        'a manifest with no nuxel.bridge_version is incompatible');
    console.log('[test] bridge_version pin + manifest check ok');

    // 6. Version mismatch must be LOUD and must NOT degrade to mock data.
    //    Drop the window token from test 3 so each client bootstraps its own.
    delete globalThis.__NUXEL_TOKEN__;
    //    (a) host declares a different protocol version.
    await new Promise((r) => server.listen(0, '127.0.0.1', r));
    PORT = server.address().port;
    VERSION_OVERRIDE = '999';
    const cVer = new NuxelBridgeClient({ apiUrl: base(), appId: 'org.nuxel.Skewed' });
    await cVer._init();
    assert.strictEqual(cVer.isConnected(), false, 'a skewed host is not a usable connection');
    assert.strictEqual(cVer.mockMode, false, 'a version mismatch must never enable mock mode');
    assert.deepStrictEqual(cVer.versionMismatch, { expected: '1', got: '999' });
    await assert.rejects(() => cVer.call('storage', 'list-dir', { path: '/' }), (e) => {
        assert.ok(e instanceof NuxelBridgeVersionError, 'thrown error is a NuxelBridgeVersionError');
        assert.strictEqual(e.code, 'NUXEL_BRIDGE_VERSION_MISMATCH');
        return true;
    });
    console.log('[test] version mismatch refused loudly (no mock fallback) ok');

    //    (b) a legacy host that declares nothing is also a mismatch.
    VERSION_OVERRIDE = null;
    const cLegacy = new NuxelBridgeClient({ apiUrl: base(), appId: 'org.nuxel.Legacy' });
    await cLegacy._init();
    assert.strictEqual(cLegacy.mockMode, false, 'legacy host must not silently enable mock mode');
    assert.deepStrictEqual(cLegacy.versionMismatch, { expected: '1', got: null });
    console.log('[test] undeclared host version refused loudly ok');

    //    (c) the healthy host is accepted, and the pin is exposed.
    VERSION_OVERRIDE = undefined;
    const cOk = new NuxelBridgeClient({ apiUrl: base(), appId: 'org.nuxel.Ok' });
    await cOk._init();
    assert.strictEqual(cOk.isConnected(), true);
    assert.strictEqual(cOk.getBridgeVersion(), NUXEL_BRIDGE_VERSION);
    console.log('[test] healthy host accepted ok');
    await new Promise((r) => server.close(r));

    console.log('\n[test] ALL TESTS PASSED');
    process.exit(0);
}

main().catch((e) => {
    console.error('[test] FAILED:', e);
    process.exit(1);
});
