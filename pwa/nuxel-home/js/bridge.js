// Nuxel Home - Bridge Client (Portal-Driven Permissions)
//
// This module now delegates to the SHARED bridge client from
// pwa/nuxel-common/bridge.js (loaded as an ES module that exposes the UMD-style
// global `window.NuxelBridge`). It keeps the home-specific convenience methods
// (phone status, sms, call, permission summary) as thin wrappers on top.
//
// `bridge` (lowercase) is the object consumed by the other home scripts. It
// resolves to the shared singleton lazily so it remains safe even if callers
// evaluate before the shared module has finished loading.

(function (global) {
    'use strict';

    // Return the shared bridge, or a minimal offline fallback if unavailable.
    function shared() {
        if (global.NuxelBridge) return global.NuxelBridge;
        // Fallback so home scripts never crash at eval time.
        return {
            connected: false,
            mockMode: true,
            appId: 'org.nuxel.Home',
            call: async function () { return { success: false }; },
            on: function () {},
            off: function () {},
            isConnected: function () { return false; },
            getCapabilities: async function () { return []; },
        };
    }

    const bridge = {
        get apiUrl() { return shared().apiUrl || 'http://127.0.0.1:8080/api/v1'; },
        get connected() { return shared().connected; },
        get appId() { return shared().appId || 'org.nuxel.Home'; },

        // ---- generic (delegated to shared client) ----
        call: function (ns, verb, params) { return shared().call(ns, verb, params); },
        on: function (ev, cb) { return shared().on(ev, cb); },
        off: function (ev, cb) { return shared().off(ev, cb); },
        isConnected: function () { return shared().isConnected(); },
        getCapabilities: function () { return shared().getCapabilities(); },
        subscribe: function (cap, ev, cb) { return shared().subscribe(cap, ev, cb); },

        // ---- capability helpers (delegated to shared client) ----
        requestCapability: function (cap, reason) { return shared().requestCapability(cap, reason); },
        hasCapability: async function (cap) {
            try { return (await shared().requestCapability(cap)) !== false; } catch (e) { return false; }
        },
        getGrantedCapabilities: async function () {
            try {
                const res = await shared().call('permissions', 'list', { app_id: this.appId });
                return (res && res.capabilities) ? res.capabilities : [];
            } catch (e) { return []; }
        },
        revokeCapability: async function (cap) {
            try { return await shared().call('permissions', 'revoke', { app_id: this.appId, capability: cap }); }
            catch (e) { return { success: false }; }
        },
        getPermissionSummary: async function () {
            const granted = await this.getGrantedCapabilities();
            return granted.map((cap) => ({
                id: cap, name: cap, granted: true,
            }));
        },
        onCapabilityChange: function (cap, cb) { shared().on('capability:' + cap, cb); },

        // ---- phone / sms / call / location / notification wrappers ----
        getPhoneStatus: async function () {
            try { return await shared().call('phone', 'status', { app_id: this.appId }); }
            catch (e) { return { modem: { connected: false }, network: { connected: false }, battery: { level: 100, charging: true } }; }
        },
        getLocation: function () { return shared().getLocation(); },
        sendSms: function (number, text) { return shared().sendSms(number, text); },
        getSmsMessages: async function () {
            try { const r = await shared().call('sms', 'list', { app_id: this.appId }); return (r && r.messages) || []; }
            catch (e) { return []; }
        },
        initiateCall: function (number) { return shared().initiateCall(number); },
        endCall: async function (callId) {
            try { return await shared().call('call', 'end', { app_id: this.appId, call_id: callId || '' }); }
            catch (e) { return { success: false }; }
        },
        sendNotification: function (title, body) { return shared().sendNotification(title, body); },
        // Read the notification store that the daemon persists to the canonical
        // JSON source /var/lib/nuxel/notifications.json (exposed via the bridge).
        // Returns { success, notifications } where notifications is the array of
        // notification dicts (id, app_id, summary, body, timestamp, urgency).
        getNotifications: async function () {
            try {
                return await shared().call('notifications', 'list', { app_id: this.appId });
            } catch (e) {
                return { success: false, notifications: [] };
            }
        },
    };

    global.bridge = bridge;
    global.haveBridge = true;

    // Re-export the shared class under the same global name for compatibility.
    global.NuxelBridgeClient = global.NuxelBridge && global.NuxelBridge.constructor;
})(window);
