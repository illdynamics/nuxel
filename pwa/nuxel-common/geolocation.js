/**
 * Nuxel Geolocation passthrough (pwa/nuxel-common/geolocation.js)
 *
 * Proxies the browser's `navigator.geolocation` API through the Nuxel bridge
 * instead of the native W3C permission gate.
 *
 * Why: native `navigator.geolocation` in a PWA triggers the WebKit/runtime
 * permission prompt and (on mustang) has no GeoClue backend wired to the
 * portal. All geolocation resolution therefore flows through:
 *
 *     PWA -> bridge.call('location', 'request', {...})
 *                 -> nuxel-bridge service
 *                     -> HM hardware: GeoClue via the xdg-desktop-portal
 *                       (org.freedesktop.GeoClue2)
 *                     -> VM: returns a synthetic location
 *
 * Contract: bridge.call('location', 'request') where 'location' is the
 * capability (declared in the app manifest under `nuxel.capabilities` as
 * `location:read`) and 'request' is the verb. Response shape:
 *
 *   { success: true, coords: { latitude, longitude, accuracy,
 *                              altitude?, altitudeAccuracy?,
 *                              heading?, speed?, timestamp } }
 *   or { success: false, code, message }
 *
 * The PWA manifest MUST NOT enable native `geolocation` (it is intentionally
 * blocked). Apps must set `nuxel.capabilities: ["location:read"]` in their
 * manifest and call the helpers below.
 */

(function (global) {
    'use strict';

    // Require an injected bridge client. nuxel-common/bridge.js installs
    // window.NuxelBridge; fall back to the per-app NuxelBridgeClient.
    function getBridge() {
        if (global.NuxelBridge) return global.NuxelBridge;
        // If a bridge class was defined locally, instantiate one.
        if (typeof NuxelBridgeClient !== 'undefined') {
            return new NuxelBridgeClient();
        }
        throw new Error('NuxelBridge not available — include nuxel-common/bridge.js first');
    }

    /**
     * Locally override navigator.geolocation so existing code that calls
     * navigator.geolocation.getCurrentPosition/watchPosition works unchanged
     * while actually routing through the bridge. The W3C permission gate is
     * intentionally bypassed; capability gating happens server-side.
     *
     * To fully disable native geolocation while keeping the shim API, call
     * installGeolocationShim() in each PWA.
     */
    function installGeolocationShim() {
        if (typeof navigator === 'undefined') return;

        const shim = {
            // Minimal spec-shaped API.
            getCurrentPosition(onsuccess, onerror, options) {
                _requestLocation(onsuccess, onerror, options);
            },
            watchPosition(onsuccess, onerror, options) {
                const id = _watchSequence++;
                _watchCallbacks.set(id, { onsuccess, onerror, options });
                _requestLocation(
                    (pos) => {
                        const w = _watchCallbacks.get(id);
                        if (w && w.onsuccess) w.onsuccess(pos);
                    },
                    (err) => {
                        const w = _watchCallbacks.get(id);
                        if (w && w.onerror) w.onerror(err);
                    },
                    options
                );
                return id;
            },
            clearWatch(id) {
                _watchCallbacks.delete(id);
            },
        };

        // Define read-only so native getter cannot be re-triggered.
        try {
            Object.defineProperty(navigator, 'geolocation', {
                configurable: false,
                enumerable: true,
                get() { return shim; },
            });
        } catch (e) {
            // Older runtimes: direct assignment.
            navigator.geolocation = shim;
        }
    }

    // --- internals ---------------------------------------------------------
    let _watchSequence = 0;
    const _watchCallbacks = new Map();

    function _requestLocation(onsuccess, onerror, options) {
        const bridge = getBridge();
        let payload = { highAccuracy: !!(options && options.accuracy) };

        // bridge.call(namespace, verb, params). The bridge service exposes
        // the 'location' capability with a 'request' verb.
        Promise.resolve(bridge.call('location', 'request', payload))
            .then((res) => {
                if (!res) return _onError(onerror, 1, 'No location reply from bridge');
                if (!res.success) {
                    return _onError(
                        onerror,
                        res.code || 1,
                        res.message || 'Location request denied'
                    );
                }
                const c = res.coords || {};
                const coords = {
                    latitude: Number(c.latitude) || 0,
                    longitude: Number(c.longitude) || 0,
                    accuracy: Number(c.accuracy) !== undefined ? Number(c.accuracy) : 65,
                    altitude: c.altitude != null ? Number(c.altitude) : null,
                    altitudeAccuracy: c.altitudeAccuracy != null ? Number(c.altitudeAccuracy) : null,
                    heading: c.heading != null ? Number(c.heading) : null,
                    speed: c.speed != null ? Number(c.speed) : null,
                };
                const position = {
                    coords,
                    timestamp: Number(c.timestamp) || Date.now(),
                    // Nuxel augmented payload
                    source: c.source || 'nuxel-bridge',
                    synthetic: !!c.synthetic,
                };
                if (onsuccess) onsuccess(position);
            })
            .catch((e) => _onError(onerror, 2, String((e && e.message) || e)));
    }

    function _onError(onerror, code, message) {
        if (onerror) {
            const err = new Error(message);
            err.code = code;
            // geolocation position-error code mapping
            err.PERMISSION_DENIED = 1;
            err.POSITION_UNAVAILABLE = 2;
            err.TIMEOUT = 3;
            onerror(err);
        }
    }

    // Convenience promise-style helpers (avoid native API for framework code).
    function getCurrentPositionAsync(options) {
        return new Promise((resolve, reject) => {
            _requestLocation(resolve, reject, options);
        });
    }

    // Export.
    const NuxelGeolocation = {
        installShim: installGeolocationShim,
        getCurrentPosition: (onSuccess, onError, options) =>
            _requestLocation(onSuccess, onError, options),
        getCurrentPositionAsync,
        watchPosition: (onSuccess, onError, options) => {
            const id = ++_watchSequence;
            _watchCallbacks.set(id, { onsuccess: onSuccess, onerror: onError, options });
            _requestLocation(
                (p) => { const w = _watchCallbacks.get(id); if (w && w.onsuccess) w.onsuccess(p); },
                (e) => { const w = _watchCallbacks.get(id); if (w && w.onerror) w.onerror(e); },
                options
            );
            return id;
        },
        clearWatch: (id) => _watchCallbacks.delete(id),
    };

    global.NuxelGeolocation = NuxelGeolocation;

    // Auto-install the navigator.geolocation shim on load so existing PWA code
    // calling navigator.geolocation routes through the bridge automatically.
    try { installGeolocationShim(); } catch (e) { /* non-browser env */ }
})((typeof window !== 'undefined' && window) ? window : globalThis);
