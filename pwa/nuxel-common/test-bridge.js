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
import { NuxelBridgeClient } from './bridge.js';

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
            return send(200, { status: 'ok', version: '0.2.0-test' });
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

    console.log('\n[test] ALL TESTS PASSED');
    process.exit(0);
}

main().catch((e) => {
    console.error('[test] FAILED:', e);
    process.exit(1);
});
