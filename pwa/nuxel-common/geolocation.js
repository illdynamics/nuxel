/**
 * Nuxel Geolocation shim (pwa/nuxel-common/geolocation.js)
 *
 * Routes the W3C `navigator.geolocation` API through the Nuxel bridge:
 *
 *     PWA -> bridge.call('location', 'acquire'|'request'|'stop')
 *         -> nuxel-bridge -> GeoClue2 -> real network/GNSS provider
 *
 * Honesty rules enforced here:
 *   - missing/NaN/Infinity/out-of-range coordinates are rejected (never 0,0);
 *   - a missing provider timestamp stays missing (never replaced by Date.now());
 *   - unknown accuracy is null (never a fabricated 5/20/65 m value);
 *   - network/Wi-Fi/IP sources are never relabelled as GPS/GNSS;
 *   - watchPosition() polls only while at least one watch is active and stops
 *     every timer when the last watch is cleared or location policy goes OFF.
 *
 * Response shape from the bridge (see services/nuxel-bridge/src/bridge.py):
 *   { success: true, latitude, longitude, accuracy, timestamp, source,
 *     source_detail, kind, gnss, network, state }
 */


(function (global) {
    'use strict';

    var DEFAULT_WATCH_INTERVAL_MS = 10000;
    var MIN_WATCH_INTERVAL_MS = 2000;
    var _watchSequence = 0;
    var _watches = new Map();
    var _schedulerTimer = null;
    var _pollInFlight = false;
    var _policySuspended = false;
    var _watchIntervalMs = DEFAULT_WATCH_INTERVAL_MS;
    var _minIntervalMs = MIN_WATCH_INTERVAL_MS;

    function getBridge() {
        if (global.NuxelBridge) return global.NuxelBridge;
        if (typeof NuxelBridgeClient !== 'undefined') return new NuxelBridgeClient();
        throw new Error('NuxelBridge not available — include nuxel-common/bridge.js first');
    }

    function finite(value) {
        // Number(null) is 0 — exactly how the old shim produced Null Island.
        if (value === null || value === undefined || value === '' ||
            typeof value === 'boolean') return null;
        var n = Number(value);
        return Number.isFinite(n) ? n : null;
    }

    function validLatLon(lat, lon) {
        if (lat === null || lon === null) return false;
        return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
    }

    function normaliseTimestamp(value) {
        var n = finite(value);
        if (n === null || n <= 0) return null;
        // GeoClue uses seconds; W3C Position.timestamp is milliseconds.
        if (n > 0 && n < 1e11) return Math.round(n * 1000);
        return Math.round(n);
    }

    function classifySource(raw, explicitGnss) {
        var source = String((raw && raw.source) || '').toLowerCase();
        var kind = String((raw && raw.kind) || '').toLowerCase();
        var gnss = explicitGnss === true || source === 'gnss' || kind === 'satellite';
        if (gnss) return { source: 'gnss', kind: 'satellite', gnss: true, network: false };
        if (/network|wifi|wi-fi|ip|cell/.test(source) || kind === 'network') {
            return { source: source || 'network', kind: 'network', gnss: false, network: true };
        }
        if (source) return { source: source, kind: kind || 'unknown', gnss: false, network: false };
        return { source: 'geoclue_unknown', kind: 'unknown', gnss: false, network: false };
    }

    function positionFromResponse(res) {
        if (!res || res.success !== true) {
            return { ok: false, code: bridgeErrorCode(res), message: (res && (res.error || res.message)) || 'Location request failed' };
        }
        var lat = finite(res.latitude);
        var lon = finite(res.longitude);
        if (!validLatLon(lat, lon)) {
            return { ok: false, code: 2, message: 'Provider returned no valid latitude/longitude' };
        }
        var acc = finite(res.accuracy);
        if (acc !== null && acc < 0) acc = null;
        var ts = normaliseTimestamp(res.timestamp);
        var src = classifySource(res, res.gnss);
        var coords = {
            latitude: lat,
            longitude: lon,
            accuracy: acc,
            altitude: finite(res.altitude),
            altitudeAccuracy: finite(res.altitudeAccuracy),
            heading: finite(res.heading),
            speed: finite(res.speed),
        };
        return {
            ok: true,
            position: {
                coords: coords,
                // A missing provider time remains null.  Consumers must treat
                // this position as lacking freshness evidence, not as fresh.
                timestamp: ts,
                timestampSource: ts === null ? 'missing' : 'provider',
                freshnessEvidence: ts !== null,
                fresh: ts !== null,
                source: src.source,
                sourceDetail: res.source_detail || null,
                kind: src.kind,
                gnss: src.gnss,
                network: src.network,
                synthetic: res.synthetic === true,
                state: res.state || null,
            },
        };
    }

    function bridgeErrorCode(res) {
        var code = res && res.error_code;
        if (code === 'CAPABILITY_DENIED' || code === 'LOCATION_DISABLED') return 1;
        if (code === 'TIMEOUT') return 3;
        return 2;
    }

    function deliverError(onerror, code, message) {
        if (!onerror) return;
        try {
            var err = new Error(message);
            err.code = code;
            err.PERMISSION_DENIED = 1;
            err.POSITION_UNAVAILABLE = 2;
            err.TIMEOUT = 3;
            onerror(err);
        } catch (e) { /* a consumer callback must not break the shim */ }
    }

    function buildPayload(options) {
        options = options || {};
        var highAccuracy = options.enableHighAccuracy === true;
        var timeout = finite(options.timeout);
        var maximumAge = finite(options.maximumAge);
        return {
            highAccuracy: highAccuracy,
            timeout: timeout === null ? null : Math.max(0, Math.round(timeout)),
            maximumAge: maximumAge === null ? null : Math.max(0, Math.round(maximumAge)),
            // Backward-compatible hint for older bridge revisions.  Never use
            // the non-standard options.accuracy field as enableHighAccuracy.
            high_accuracy: highAccuracy,
        };
    }

    function requestLocation(options) {
        var bridge = getBridge();
        var payload = buildPayload(options);
        return Promise.resolve(bridge.call('location', 'request', payload)).then(function (res) {
            return positionFromResponse(res);
        }, function (e) {
            return { ok: false, code: 2, message: String((e && e.message) || e) };
        });
    }

    function acquireLocation(options) {
        var bridge = getBridge();
        var payload = buildPayload(options);
        // Prefer the explicit acquisition verb: it records a client lease and
        // can restart an idle/stopped GeoClue without claiming a fix.
        return Promise.resolve(bridge.call('location', 'acquire', payload)).then(function (res) {
            if (res && res.success === false && res.error_code === 'CAPABILITY_DENIED') {
                // Do not bypass the Nuxel permission model: return the error.
                return res;
            }
            return res;
        }, function (e) {
            return { success: false, error_code: 'PROVIDER_ERROR', error: String((e && e.message) || e) };
        });
    }

    function locationFromAcquire(res) {
        if (!res) return { ok: false, code: 2, message: 'No location reply from bridge' };
        if (res.success === true && res.latitude != null && res.longitude != null) {
            return positionFromResponse(res);
        }
        // LocationAcquire returns provider status.  Only a fixed state may be
        // turned into a Position; searching/no_fix are real errors.
        if (res.state === 'fixed' && res.latitude != null && res.longitude != null) {
            return positionFromResponse(res);
        }
        return {
            ok: false,
            code: bridgeErrorCode(res),
            message: res.detail || res.error || ('Location state: ' + (res.state || 'unavailable')),
            state: res.state || null,
        };
    }

    function stopAcquisition() {
        var bridge;
        try { bridge = getBridge(); } catch (e) { return Promise.resolve(); }
        try {
            return Promise.resolve(bridge.call('location', 'stop', {})).catch(function () {});
        } catch (e) {
            return Promise.resolve();
        }
    }

    function _onError(onerror, code, message) {
        deliverError(onerror, code, message);
    }

    function getCurrentPosition(onsuccess, onerror, options) {
        var timeoutMs = finite(options && options.timeout);
        var settled = false;
        var timer = null;
        function finishError(code, message) {
            if (settled) return;
            settled = true;
            if (timer) clearTimeout(timer);
            deliverError(onerror, code, message);
        }
        var promise = acquireLocation(options).then(locationFromAcquire).then(function (out) {
            if (settled) return;
            if (!out.ok) { finishError(out.code, out.message); return; }
            settled = true;
            if (timer) clearTimeout(timer);
            if (onsuccess) onsuccess(out.position);
            // A one-shot request is not a watch: release the acquisition as
            // soon as the caller receives the result, unless a watch still
            // needs the provider.
            if (_watches.size === 0) stopAcquisition();
        });
        if (timeoutMs !== null && timeoutMs > 0) {
            timer = setTimeout(function () {
                finishError(3, 'Location request timed out');
            }, timeoutMs);
        }
        return promise;
    }

    function watchTick() {
        if (_pollInFlight || _watches.size === 0 || _policySuspended) return;
        _pollInFlight = true;
        // Merge the active watches' W3C options for this poll: any caller that
        // requested high accuracy gets it; use the shortest timeout and the
        // largest accepted maximumAge.
        var highAccuracy = false;
        var timeoutMs = null;
        var maximumAge = null;
        _watches.forEach(function (w) {
            var o = w.options || {};
            if (o.enableHighAccuracy === true) highAccuracy = true;
            var t = finite(o.timeout);
            if (t !== null && t > 0 && (timeoutMs === null || t < timeoutMs)) timeoutMs = t;
            var a = finite(o.maximumAge);
            if (a !== null && (maximumAge === null || a > maximumAge)) maximumAge = a;
        });
        var tickOptions = { enableHighAccuracy: highAccuracy, timeout: timeoutMs, maximumAge: maximumAge };
        var poll = acquireLocation(tickOptions);
        if (timeoutMs !== null && timeoutMs > 0) {
            poll = Promise.race([poll, new Promise(function (resolve) {
                setTimeout(function () {
                    resolve({ success: false, error_code: 'TIMEOUT', error: 'Location watch poll timed out' });
                }, timeoutMs);
            })]);
        }
        poll.then(locationFromAcquire).then(function (out) {
            _pollInFlight = false;
            if (_watches.size === 0) {
                stopAcquisition();
                return;
            }
            if (!out.ok) {
                if (out.code === 1 && /disabled|denied/i.test(String(out.message || ''))) {
                    // Global policy is OFF (or permission revoked): stop all
                    // timers immediately and report the real error.
                    _policySuspended = true;
                    stopScheduler();
                    _watches.forEach(function (w) { deliverError(w.onerror, 1, out.message || 'Location is disabled'); });
                    return;
                }
                _watches.forEach(function (w) { deliverError(w.onerror, out.code, out.message); });
                return;
            }
            var p = out.position;
            var signature = p.coords.latitude + ',' + p.coords.longitude + ',' +
                String(p.timestamp) + ',' + String(p.coords.accuracy) + ',' + p.source;
            _watches.forEach(function (w) {
                if (w.lastSignature === signature) return;
                w.lastSignature = signature;
                if (w.onsuccess) {
                    try { w.onsuccess(p); } catch (e) { /* consumer error is isolated */ }
                }
            });
        }, function (e) {
            _pollInFlight = false;
            if (_watches.size === 0) return;
            _watches.forEach(function (w) { deliverError(w.onerror, 2, String((e && e.message) || e)); });
        });
    }

    function scheduleDelayMs() {
        var min = _watchIntervalMs;
        _watches.forEach(function (w) {
            if (w.intervalMs < min) min = w.intervalMs;
        });
        return Math.max(_minIntervalMs, min);
    }

    function ensureScheduler() {
        if (_schedulerTimer || _watches.size === 0 || _policySuspended) return;
        var delay = scheduleDelayMs();
        _schedulerTimer = setTimeout(function () {
            _schedulerTimer = null;
            watchTick();
            ensureScheduler();
        }, delay);
    }

    function stopScheduler() {
        if (_schedulerTimer) {
            clearTimeout(_schedulerTimer);
            _schedulerTimer = null;
        }
    }

    function restartScheduler() {
        stopScheduler();
        if (_watches.size === 0) return;
        ensureScheduler();
    }

    function watchPosition(onsuccess, onerror, options) {
        var id = ++_watchSequence;
        var intervalMs = finite(options && options.watchInterval);
        if (intervalMs === null) intervalMs = _watchIntervalMs;
        _watches.set(id, {
            onsuccess: onsuccess,
            onerror: onerror,
            options: options || {},
            intervalMs: Math.max(_minIntervalMs, intervalMs),
            lastSignature: null,
        });
        _policySuspended = false;
        restartScheduler();
        // Fire the first acquisition promptly (the first scheduler tick may be
        // up to one interval away).
        setTimeout(function () {
            if (_watches.has(id)) watchTick();
        }, 0);
        return id;
    }

    function clearWatch(id) {
        if (!_watches.has(id)) return;
        _watches.delete(id);
        if (_watches.size === 0) {
            stopScheduler();
            if (!_pollInFlight) stopAcquisition();
        } else {
            restartScheduler();
        }
    }

    function installGeolocationShim() {
        if (typeof navigator === 'undefined') return;
        var shim = {
            getCurrentPosition: function (onsuccess, onerror, options) {
                getCurrentPosition(onsuccess, onerror, options);
            },
            watchPosition: function (onsuccess, onerror, options) {
                return watchPosition(onsuccess, onerror, options);
            },
            clearWatch: function (id) { clearWatch(id); },
        };
        try {
            Object.defineProperty(navigator, 'geolocation', {
                configurable: false,
                enumerable: true,
                get: function () { return shim; },
            });
        } catch (e) {
            navigator.geolocation = shim;
        }
    }

    // Resume watches after Location is re-enabled from Quick Settings.
    try {
        if (global.document && global.document.addEventListener) {
            global.document.addEventListener('nuxel:location-policy', function (ev) {
                var enabled = !!(ev && ev.detail && ev.detail.enabled);
                if (!enabled) {
                    _policySuspended = true;
                    stopScheduler();
                } else if (_watches.size > 0) {
                    _policySuspended = false;
                    restartScheduler();
                }
            });
        }
    } catch (e) { /* non-browser environment */ }

    function getCurrentPositionAsync(options) {
        return new Promise(function (resolve, reject) {
            getCurrentPosition(resolve, reject, options);
        });
    }

    var NuxelGeolocation = {
        installShim: installGeolocationShim,
        getCurrentPosition: getCurrentPosition,
        getCurrentPositionAsync: getCurrentPositionAsync,
        watchPosition: watchPosition,
        clearWatch: clearWatch,
        // Test/diagnostic hooks (not part of the W3C API).
        _setWatchIntervalForTests: function (ms) {
            var n = finite(ms);
            if (n !== null) {
                _watchIntervalMs = Math.max(10, n);
                _minIntervalMs = Math.max(10, n);
            }
        },
        _activeWatchCount: function () { return _watches.size; },
        _hasScheduler: function () { return _schedulerTimer !== null; },
        _classifySource: classifySource,
        _positionFromResponse: positionFromResponse,
        _buildPayload: buildPayload,
    };

    global.NuxelGeolocation = NuxelGeolocation;
    if (typeof module !== 'undefined' && module.exports) module.exports = NuxelGeolocation;
    try { installGeolocationShim(); } catch (e) { /* non-browser env */ }
})((typeof window !== 'undefined' && window) ? window : globalThis);
