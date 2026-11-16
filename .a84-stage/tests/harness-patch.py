p='harness.js'
s=open(p,encoding='utf-8').read()
start=s.index("  const serverPin = opts.pin || '3838';")
end=s.index("  window.NuxelHost = {")
new_block = """  const serverPin = opts.pin || '3838';
  // Production-shape bridge client: the credential path posts security RPCs
  // through this session-aware client, so the test must exercise it too.
  function rpc(ns, verb, p) {
    state.calls.push([ns, verb, p]);
    if (ns === 'security' && verb === 'status') return Promise.resolve(Object.assign({}, state));
    if (ns === 'security' && verb === 'unlock') {
      const ok = state.mode === 'swipe' ? true : String(p.secret) === serverPin;
      if (ok) state.locked = false;
      return Promise.resolve(ok ? { success: true, unlocked: !state.locked, locked: state.locked }
                               : { success: false, error: 'invalid_credential', locked: true });
    }
    if (ns === 'security' && verb === 'lock') { state.locked = true; return Promise.resolve({ success: true }); }
    if (ns === 'fingerprint') return Promise.resolve({ success: true, ready: !!state.fingerprint.provider_ready });
    return Promise.resolve({ success: true });
  }
  window.NuxelBridge = { call: (ns, verb, p) => rpc(ns, verb, p) };
  window.securityBootstrap = {
    status() { return Promise.resolve(Object.assign({}, state)); },
    lock(reason) { state.locked = true; state.calls.push(['lock', reason]); return Promise.resolve({ success: true }); },
    unlockSwipe() {
      state.calls.push(['unlockSwipe']);
      if (state.mode !== 'swipe') return Promise.resolve({ ok: false, error: 'credential-required-on-lockscreen', mode: state.mode });
      if (!state.locked) return Promise.resolve({ ok: true, state: 'UNLOCKED' });
      state.locked = false; return Promise.resolve({ ok: true, state: 'UNLOCKED', via: 'swipe' });
    },
    verifyUnlock() { return Promise.resolve(state.locked ? { ok: false } : { ok: true }); },
    setMode(mode) { state.mode = mode; state.locked = true; return Promise.resolve({ success: true }); },
    call: (ns, verb, p) => rpc(ns, verb, p),
  };
"""
s = s[:start] + new_block + s[end:]
s=s.replace("""  // The REAL security-lock.js is loaded by the test; eval it against the same fake window first.
  window.__realSecurityLock = async function () {
    const src = await Deno.readTextFile(new URL('../pwa/nuxel-home/js/security-lock.js', import.meta.url));
    new Function('window', 'document', 'console', 'fetch', src)(window, doc, console, () => Promise.reject(new Error('no fetch')));
  };""","  window.__serverState = state;")
open(p,'w',encoding='utf-8').write(s)
print('ok')
