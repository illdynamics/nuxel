/**
 * Nuxel shared bridge client (pwa/nuxel-common/bridge.js)
 *
 * A single bridge client shared by every PWA. Loaded as an ES module:
 *
 *     <script type="module" src=".../bridge.js"></script>
 *
 * As a module it both exports named entry points and sets the UMD-style
 * global `window.NuxelBridge` (and `window.NuxelBridgeClient`) so classic
 * scripts that defer until after load can also use the shared singleton.
 *
 * Exposes:
 *   - `call(namespace, verb, params)` — generic bridge RPC with a mock
 *     fallback when the bridge is unreachable.
 *   - `subscribe(capability, event, callback)` — SSE subscription via
 *     `/bridge/subscribe` (falls back to a local event bus if SSE fails).
 *   - `on` / `off` local event bus, capability helpers, native wrappers.
 *
 * Token resolution order (first source that yields a token wins):
 *   1. `window.__NUXEL_TOKEN__`   (injected by the native PWA launcher)
 *   2. `/var/lib/nuxel/.api-token` (local API token file)
 *   3. `localStorage['nuxel-bridge-token']` (dev fallback)
 *   Otherwise a per-session token is bootstrapped from `POST /auth/token`.
 */

const API_URL = (typeof globalThis !== 'undefined' && globalThis.NUXEL_API_URL) ||
    'http://127.0.0.1:8080/api/v1';

// Local fallback data used when the bridge is unreachable (mock mode).
const MOCK_STORE = {};

export class NuxelBridgeClient {
    constructor(opts) {
        opts = opts || {};
        this.apiUrl = opts.apiUrl || API_URL;
        this.appId = opts.appId || (typeof document !== 'undefined' && document.querySelector && document.querySelector('meta[name="nuxel-app-id"]')
            ? document.querySelector('meta[name="nuxel-app-id"]').content
            : 'org.nuxel.Platform');
        this.token = '';
        this.connected = false;
        this.mockMode = false;
        this.capabilities = new Map();
        this.listeners = new Map();
        this._sseSources = new Map();
        this._seen = new Set();
        this._initPromise = null;
    }

    /* ---- Token acquisition ---- */

    async _resolveToken() {
        const g = typeof window !== 'undefined' ? window : globalThis;

        // 1. window.__NUXEL_TOKEN__ (injected by the native PWA launcher)
        if (g.__NUXEL_TOKEN__) {
            this.token = g.__NUXEL_TOKEN__;
            this._persistToken(this.token);
            return this.token;
        }

        // 2. /var/lib/nuxel/.api-token (local API token file)
        try {
            const fileRes = await fetch('/var/lib/nuxel/.api-token');
            if (fileRes && fileRes.ok) {
                const body = (await fileRes.text()).trim();
                if (body) {
                    this.token = body;
                    this._persistToken(body);
                    return body;
                }
            }
        } catch (e) { /* not reachable from a plain browser page */ }

        // 3. localStorage fallback
        try {
            const local = (g.localStorage && g.localStorage.getItem('nuxel-bridge-token')) || '';
            if (local) {
                this.token = local;
                return local;
            }
        } catch (e) { /* localStorage unavailable */ }

        // 4. No local token — bootstrap a per-session token from the server.
        try {
            const res = await fetch(this.apiUrl + '/auth/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_id: this.appId }),
            });
            if (res.ok) {
                const data = await res.json();
                if (data && data.token) {
                    this.token = data.token;
                    this._persistToken(data.token);
                    return this.token;
                }
            }
        } catch (e) { /* bridge unreachable — mock mode */ }

        return this.token;
    }

    _persistToken(token) {
        try {
            if (typeof localStorage !== 'undefined' && localStorage) {
                localStorage.setItem('nuxel-bridge-token', token);
            }
        } catch (e) { /* ignore */ }
    }

    async _init() {
        if (this._initPromise) return this._initPromise;
        this._initPromise = (async () => {
            try {
                await this._resolveToken();
                const ping = await this._request('/ping', { message: 'init' });
                if (ping && (ping.status === 'ok' || ping.success === true)) {
                    this.connected = true;
                    this.mockMode = false;
                    this._loadCapabilities();
                }
            } catch (e) {
                this.connected = false;
                this.mockMode = true;
                console.warn('[Bridge] not connected, using mock fallback:', e && e.message);
            }
        })();
        return this._initPromise;
    }

    /* ---- Low-level request ---- */

    async _request(endpoint, data, method) {
        method = method || 'GET';
        const url = this.apiUrl + endpoint;
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (this.token) options.headers['Authorization'] = 'Bearer ' + this.token;
        if (method === 'POST') options.body = JSON.stringify(data || {});
        const res = await fetch(url, options);
        if (!res.ok) throw new Error('bridge HTTP ' + res.status);
        return res.json();
    }

    async _loadCapabilities() {
        try {
            const caps = await this._request('/capabilities', { app_id: this.appId });
            const list = (caps && caps.capabilities) ? caps.capabilities : [];
            (list || []).forEach((c) => {
                const id = c && (c.id || c);
                if (id) this.capabilities.set(id, true);
            });
        } catch (e) { /* ignore */ }
    }

    /* ---- Generic RPC with mock fallback ---- */

    async call(namespace, verb, params) {
        await this._init();
        const payload = { app_id: this.appId, namespace, verb, params: params || {} };
        try {
            const res = await this._request('/rpc', payload, 'POST');
            if (res && res.result !== undefined) {
                this.connected = true;
                this.mockMode = false;
                return res.result;
            }
            if (res && res.success === false) throw new Error((res.error) || ('bridge error on ' + namespace + '.' + verb));
            return res;
        } catch (e) {
            // Graceful mock fallback when the bridge is unreachable.
            this.connected = false;
            this.mockMode = true;
            return this._mockCall(namespace, verb, payload.params);
        }
    }

    _mockCall(namespace, verb, params) {
        const key = [namespace, verb].join('.');
        switch (key) {
            case 'storage.write':
                MOCK_STORE[params.key || params.path] = params.data;
                return { success: true, mock: true };
            case 'storage.read':
                return { success: true, data: MOCK_STORE[params.key || params.path] || null, mock: true };
            case 'caldav.list':
                return { success: true, events: (MOCK_STORE['caldav:events'] || []), mock: true };
            case 'caldav.put':
                MOCK_STORE['caldav:events'] = params.events || [];
                return { success: true, mock: true };
            case 'camera.list-captures':
                return { success: true, captures: (MOCK_STORE['camera:captures'] || []), mock: true };
            case 'camera.capture':
                MOCK_STORE['camera:captures'] = params.captures || MOCK_STORE['camera:captures'] || [];
                if (params && params.capture) MOCK_STORE['camera:captures'].unshift(params.capture);
                return { success: true, mock: true };
            case 'storage.list-dir':
                return { success: true, entries: (MOCK_STORE['storage:dir:' + (params.path || '/')] || []), mock: true };
            case 'mail.imap-list':
                return { success: true, messages: (MOCK_STORE['mail:messages'] || []), mock: true };
            case 'mail.smtp-send':
                return { success: true, mock: true };
            default:
                return { success: true, mock: true, _key: key };
        }
    }

    /* ---- SSE subscription ---- */

    subscribe(capability, event, callback) {
        const subKey = capability + ':' + event;
        this.on(subKey, callback);

        // Attempt a real SSE connection; fall back to the local bus only.
        if (typeof EventSource === 'function') {
            if (!this._sseSources.has(subKey)) {
                let url = this.apiUrl + '/bridge/subscribe';
                url += '?capability=' + encodeURIComponent(capability) + '&event=' + encodeURIComponent(event);
                if (this.appId) url += '&app_id=' + encodeURIComponent(this.appId);
                try {
                    const es = new EventSource(url);
                    es.onmessage = (evt) => {
                        let data = evt.data;
                        try { data = JSON.parse(data); } catch (e) { /* keep string */ }
                        this._emit(subKey, data);
                        this._emit(event, data);
                    };
                    es.onerror = () => { /* SSE unavailable — local bus still works */ };
                    this._sseSources.set(subKey, es);
                } catch (e) { /* EventSource unsupported */ }
            }
        }
        return () => {
            this.off(subKey, callback);
            const es = this._sseSources.get(subKey);
            if (es) { es.close(); this._sseSources.delete(subKey); }
        };
    }

    /* ---- Capability + native wrappers ---- */

    async requestCapability(capability, reason) {
        return this.call('permissions', 'request', { capability, reason });
    }

    // Alias used by several PWA apps (e.g. calendar) for portal permission
    // requests. Returns { granted:boolean, ... } to match the portal contract.
    async requestPermission(capability, reason) {
        try {
            const res = await this.call('permissions', 'request', { capability, reason });
            if (res && res.success === false) return { granted: false, error: res.error };
            return { granted: true, ...((res && res.result) || {}) };
        } catch (e) {
            return { granted: false, error: e && e.message };
        }
    }

    async getLocation() {
        return this.call('location', 'request', {});
    }

    async sendSms(number, text) {
        return this.call('sms', 'send', { number, text });
    }

    async initiateCall(number) {
        return this.call('call', 'initiate', { number });
    }

    async getCameraNode() {
        return this.call('camera', 'request', {});
    }

    async sendNotification(title, body) {
        return this.call('notifications', 'send', { title, body });
    }

    async getCapabilities() {
        await this._init();
        const caps = [];
        this.capabilities.forEach((v, k) => v && caps.push(k));
        return caps;
    }

    isConnected() {
        return this.connected;
    }

    isMockMode() {
        return this.mockMode;
    }

    /* ---- Local event bus ---- */

    on(event, cb) {
        if (!this.listeners.has(event)) this.listeners.set(event, []);
        this.listeners.get(event).push(cb);
    }

    off(event, cb) {
        const list = this.listeners.get(event) || [];
        this.listeners.set(event, list.filter((x) => x !== cb));
    }

    _emit(event, data) {
        (this.listeners.get(event) || []).forEach((cb) => {
            try { cb(data); } catch (e) { console.error(e); }
        });
    }
}

// Shared singleton instance + UMD-style global exposure.
const g = typeof window !== 'undefined' ? window : globalThis;
const shared = (g.NuxelBridge instanceof NuxelBridgeClient)
    ? g.NuxelBridge
    : new NuxelBridgeClient();
g.NuxelBridge = shared;
// Lowercase convenience alias so existing app code that referenced
// `window.nuxelBridge` keeps working against the same shared singleton.
g.nuxelBridge = shared;
g.NuxelBridgeClient = NuxelBridgeClient;

if (typeof addEventListener === 'function') {
    addEventListener('load', () => shared && shared._init && shared._init());
}

export { shared as bridge };
export const NuxelBridge = shared;
