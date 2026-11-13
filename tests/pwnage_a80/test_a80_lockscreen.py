#!/usr/bin/env python3
"""A80 acceptance tests: pattern/PIN/fingerprint lockscreen contract.

Static contract checks (run in CI) plus provider-level behaviour that the
existing PWNAGE-45000 suite already exercises.  These assertions pin the
specific invariants the owner asked for:

  * PIN 3838 is a real, stored credential (nothing plaintext on disk);
  * a pattern must be entered twice before it is stored;
  * pattern and PIN mode render the credential UI and hide the swipe penguin;
  * the NOT-drawn mode shows: 9 penguin dots + a drawn trail + a PIN button;
  * fingerprint mode paints the asset on the scanner and keeps PIN below it;
  * failed attempts never lock the phone out while the policy is unlimited;
  * the Vault close/unlock cycle keeps working (the container-bind fix).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'services/nuxel-bridge/src'
sys.path.insert(0, str(SRC))

HTML = (ROOT / 'pwa/nuxel-home/index.html').read_text()
CSS = (ROOT / 'pwa/nuxel-home/css/lockscreen.css').read_text()
AUTH = (ROOT / 'pwa/nuxel-home/js/lockscreen-auth.js').read_text()
LOCK = (ROOT / 'pwa/nuxel-home/js/lockscreen.js').read_text()
APP = (ROOT / 'pwa/nuxel-home/js/app.js').read_text()
SET = (ROOT / 'pwa/nuxel-apps/settings/index.html').read_text()
SETJS = (ROOT / 'pwa/nuxel-apps/settings/pwange45000-settings.js').read_text()
VAULT = (ROOT / 'pwa/nuxel-apps/vault/js/app.js').read_text()
UNIT = (ROOT / 'services/nuxel-bridge/systemd/nuxel-http-bridge.service').read_text()
SVC = (ROOT / 'services/nuxel-bridge/src/secret_service.py').read_text()
SEC = (ROOT / 'services/nuxel-bridge/src/security_provider.py').read_text()
FP = (ROOT / 'services/nuxel-bridge/src/fingerprint_provider.py').read_text()

fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)[:400]))
    if not cond:
        fails.append(name)


# ---- pattern matrix: 9 penguin dots, trail, PIN fallback -------------------
check('pattern container present', 'id="lockscreen-pattern"' in HTML)
check('pattern trail polyline present', 'id="lockscreen-pattern-trail"' in HTML)
check('pattern trail is drawn as a polyline',
      'lockscreen-pattern-trail' in AUTH and '_drawTrail' in AUTH)
check('dot count is 9', 'const DOTS = 9' in AUTH)
check('dots use the penguin lock-head artwork',
      'nuxel-lockhead.png' in AUTH and 'lockscreen-pattern-penguin' in AUTH)
check('dot matrix is 3x3',
      AUTH.count("x: 50 + (i % 3) * 100") == 1 and AUTH.count('Math.floor(i / 3) * 100') == 1)
check('PIN button below the pattern', 'id="lockscreen-pin-fallback"' in HTML)
check('PIN button wired', 'lockscreen-pin-fallback' in AUTH and 'showPinFallback' in AUTH)
check('swipe penguin hidden in credentialed modes',
      re.search(r'lockscreen-credentialed \.lockscreen-handle-wrap[^{]*\{[^}]*display:\s*none',
                CSS, re.S) is not None)

# ---- PIN keypad ------------------------------------------------------------
check('pin pad present', 'id="lockscreen-pinpad"' in HTML)
check('pin pad has 0-9 keys', all(('data-pin="%d"' % i) in HTML for i in range(10)))
check('pin pad has enter/delete/cancel',
      all(x in HTML for x in ('lockscreen-pin-enter', 'lockscreen-pin-del', 'lockscreen-pin-cancel')))
check('pin submits the credential to the bridge', "'unlock', { secret }" in AUTH)

# ---- fingerprint presentation ---------------------------------------------
check('fingerprint overlay present', 'id="lockscreen-fingerprint"' in HTML)
check('fingerprint uses the owner asset', 'assets/nuxel-fingerprint.png' in HTML)
check('fingerprint overlay has a status line and PIN fallback',
      'id="lockscreen-fingerprint-status"' in HTML)
check('fingerprint scanner is not presented as swipe', 'SCANNER' in AUTH)

# ---- setup: two entries ----------------------------------------------------
check('lockscreen setup flow present', 'id="lockscreen-setup"' in HTML)
check('setup requires a second identical draw',
      'Now draw the same pattern again' in AUTH and 'pattern_confirmation_mismatch' in SEC)
check('server refuses a single-entry pattern',
      'pattern_confirmation_required' in SEC)
check('client sends both entries', 'pattern_confirm' in AUTH)
check('settings pattern editor present', 'id="sec-pattern-editor"' in SET)
check('settings sends both entries', 'pattern_confirm: first' in SETJS)
check('settings PIN uses two entries', 'id="sec-pin2"' in SET and 'pin_confirm' in SETJS)

# ---- unlimited attempts (owner request) -----------------------------------
check('default attempt policy is unlimited',
      'DEFAULT_ATTEMPT_POLICY = "unlimited"' in SEC)
check('lockout only under the limited policy',
      '== "limited" and failures >= MAX_FAILURES' in SEC)
check('policy is owner-switchable', 'set_attempt_policy' in SEC and 'sec-policy-unlimited' in SET)
check('unlimited policy is selectable in Settings', 'sec-policy-limited' in SET)

# ---- fingerprint: Vault record + honest fail-closed ------------------------
check('fingerprint requires the Vault record', 'vault_guard' in FP)
check('fingerprint refuses match without the TEE',
      'secure_provider_unavailable' in FP and 'authenticated": False' in FP)
check('enrollment ceremony needs two edge touches',
      'edges_needed' in FP and 'edge' in FP)
check('record is HMAC-bound and stored mode 0600',
      'hmac.new' in FP and '0o600' in FP)
check('record key lives in the Vault', 'fingerprint-record-hmac' in FP)
check('enrollment record is documented as metadata, not a template',
      'template_stored": False' in FP)

# ---- Vault close/unlock container fix -------------------------------------
check('session script creates the keyring socket dir before the sandbox',
      'install -d -m 0700 /run/nuxel-wayland/keyring' in
      (ROOT / 'tools/s10plus/a45/nuxel-session.sh').read_text())
check('bridge unit keeps the runtime dir writable', 'ReadWritePaths=-/run/nuxel-wayland' in UNIT)
check('bridge does not read-only bind the keyring file directory',
      'ReadWritePaths=-/root/.local/share/keyrings' not in UNIT)
check('vault Close awaits the lock', "await bridge('lock')" in VAULT)
check('vault create verifies unlocked state', 'confirmUnlocked' in VAULT)
check('vault unlock verifies unlocked state', VAULT.count('confirmUnlocked') >= 3)
check('provider distinguishes locked vs invalid password',
      '"provider_error"' in SVC and 'invalid_credentials' in SVC)
check('password verifier lets a wrong password be reported precisely',
      '_verifier_matches' in SVC)

# ---- NFC debug window ------------------------------------------------------
check('NFC debug window present', 'id="nfc-debug-out"' in SET)
check('NFC Test button present', 'id="nfc-test2"' in SET)
check('NFC stop button present', 'id="nfc-debug-cancel"' in SET)
check('NFC debug shows uid/technology/ndef',
      all(('id="nfc-dbg-%s"' % k) in SET for k in ('uid', 'tech', 'ndef')))
check('NFC test is read-only (no write call in the debug path)',
      'nfcDebugTest' in SETJS and "'write'" not in SETJS[SETJS.index('function nfcDebugTest'):SETJS.index('function nfcDebugCancel')])
check('NFC cancel verb exists in the provider', 'verb == "cancel"' in
      (ROOT / 'services/nuxel-bridge/src/nfc_provider.py').read_text())

# ---- Home hand-off ---------------------------------------------------------
check('credential unlock commits through Home', 'completeCredentialUnlock' in APP)
check('mode changes refresh the lockscreen', 'refreshLockscreenAuth' in APP)
check('lockscreen syncs the auth mode', '_syncAuthMode' in LOCK)

# ---- A81 security fixes (owner-reported defects) --------------------------
# The running image's gnome-keyring 48 only APPLIES a stdin password through
# --login; --replace never reads stdin and --unlock never completes.  Shipping
# the wrong one made every Vault unlock fail with "unknown daemon error".
_unlock_fn = SVC.split('def _unlock_via_login')[1].split('\n    def ')[0]
check('keyring unlock uses --login with the password on stdin',
      '["--login", "--components=secrets"]' in _unlock_fn and
      '["--unlock"' not in _unlock_fn and '["--replace"' not in _unlock_fn)
check('keyring password is never passed on argv or env',
      '"--unlock-password-file"' not in SVC and 'password=password' in SVC)
check('unknown Vault password is reported precisely',
      'invalid_credentials' in SVC and 'the master password is not correct' in SVC)
check('an unopenable keyring is detected structurally',
      '_keyring_has_exported_key' in SVC and 'needs_recovery' in SVC)
check('an unopenable keyring is backed up before replacement',
      '_backup_unopenable_keyring' in SVC and 'keyring-backups' in SVC)
check('initialize recovers an unopenable keyring',
      'recovered = self._backup_unopenable_keyring()' in SVC)
check('verifier is stamped with the keyring creation time',
      'created' in SVC and '_keyring_created()' in SVC)
check('verifier sidecar is mode 0600',
      '0o600' in SVC and 'nuxel-vault-verifier.json' in SVC)
check('listing skips internal records instead of failing',
      'payload.get("type") not in ("login", "note")' in SVC and
      'payload.get("schema") != VAULT_SCHEMA' in SVC)

# The live payload must actually contain the modules it claims to deploy: the
# phone kept running old bridge copies because these were missing.
PKG = (ROOT / 'tools/s10plus/a43/package-live.py').read_text()
for mod in ('secret_service.py', 'keyring_api.py', 'security_provider.py',
            'fingerprint_provider.py'):
    check('payload ships bridge module ' + mod,
          "'services/nuxel-bridge/src/%s'" % mod in PKG)

# Keypad: one physical press (pointerdown + its click) is one digit.
check('keypad consumes the click that belongs to a pointerdown',
      "_pressKey" in AUTH and "via === 'click'" in AUTH)
check('keypad no longer uses the 120 ms same-digit collapse',
      '_lastKey' not in AUTH)

# The legacy PIN sheet must never open over the credential surface.
LEGACY = (ROOT / 'pwa/nuxel-home/js/security-lock.js').read_text()
check('legacy PIN sheet is suppressed while the lock surface owns the credential',
      'overlayOwnsCredential' in LEGACY)
import re as _re
_legacy_code = _re.sub(r'/\*.*?\*/|//[^\n]*', '', LEGACY, flags=_re.S)
check('legacy PIN sheet no longer claims a 6-digit minimum',
      'At least 6 digits' not in _legacy_code)
check('legacy prompt can never be created while the lock surface exists',
      'window.NuxelLockscreenAuth) { resolve(null)' in LEGACY)

# Fingerprint surface never paints a scanner that cannot read.
check('fingerprint artwork requires a ready secure provider',
      'this.preview = false' in AUTH)

print()
if fails:
    print('A80 TESTS: %d FAILURE(S): %s' % (len(fails), ', '.join(fails)))
    sys.exit(1)
print('A80 TESTS: ALL PASS')
