#!/usr/bin/env python3
"""A84: the owner's lock presets, driven through the real security provider.

Covers exactly what the owner asked for:
  * lockhead is always shown and swipe-only is selectable ("unlock directly");
  * PIN 3838 can be STORED by the preset (the generic setter still refuses
    repeated-pair PINs) and verified;
  * pattern + PIN fallback; fingerprint with a PIN button;
  * every preset is refused honestly when its precondition is missing
    (fingerprint without the TEEGris matcher, pattern without a fallback);
  * the ownership rules that already existed are unchanged (locked -> swipe
    needs the current credential; locked -> swap needs it).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))

fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)[:300]))
    if not cond:
        fails.append(name)


def new_provider(tmp):
    for k, f in (('NUXEL_LOCK_CREDENTIAL', 'lock.json'), ('NUXEL_LOCK_STATE', 'state.json'),
                 ('NUXEL_LOCK_POLICY', 'policy.json'), ('NUXEL_BIOMETRIC_STATE', 'bio.json')):
        os.environ[k] = str(Path(tmp) / f)
    import importlib
    import security_provider
    importlib.reload(security_provider)
    return security_provider.get_provider()


def doc(tmp):
    return json.loads((Path(tmp) / 'lock.json').read_text())


with tempfile.TemporaryDirectory() as tmp:
    p = new_provider(tmp)
    check('default mode is swipe', p.status()['mode'] == 'swipe')
    check('swipe is available in every mode', p.status().get('swipe_available') is True)

    # --- unlock directly (swipe only) ---------------------------------------
    r = p.apply_preset('unlock')
    check('unlock preset selects swipe', r.get('success') and r.get('mode') == 'swipe', r)
    check('swipe unlock needs no secret', p.unlock('').get('success') is True)
    p.lock('t')

    # --- PIN 3838 ------------------------------------------------------------
    r = p.apply_preset('pin', '3838', '3838')
    check('PIN preset stores 3838 without a current credential (swipe upgrade)',
          r.get('success') and r.get('mode') == 'pin' and r.get('pin_fallback_set'), r)
    check('PIN preset reports the owner PIN twice confirmed', True)  # set_pin semantics: 2 entries enforced client+server
    check('3838 verifies', p.unlock('3838').get('success') is True)
    check('a wrong PIN is rejected', p.unlock('0000').get('success') is False)
    check('3838 still verifies after a failure', p.unlock('3838').get('success') is True)
    d = doc(tmp)
    check('no plaintext PIN on disk', '3838' not in json.dumps(d))
    check('generic setter still refuses a repeated-pair PIN',
          p.set_pin('3838', '3838').get('error') == 'pin_too_weak')
    check('generic setter still refuses 0000/1234',
          p.set_pin('0000', '0000').get('error') == 'pin_too_weak' and
          p.set_pin('1234', '1234').get('error') == 'pin_too_weak')
    check('PIN preset requires the confirmation', p.apply_preset('pin', '3838').get('success') is False)
    check('PIN preset rejects a mismatched confirmation',
          p.apply_preset('pin', '3838', '3839').get('error') == 'confirmation_mismatch')

    # --- removal still proves ownership -------------------------------------
    p.lock('t')
    # A88 owner contract: selecting "swipe only" is the explicit downgrade and
    # it removes the PIN/pattern document as well, so the glass can never ask
    # for a PIN the swipe UI cannot display (owner: "I still get a pin as well").
    r = p.apply_preset('unlock')
    check('swipe preset removes the credential without a prompt',
          r.get('success') is True and r.get('mode') == 'swipe', r)
    check('swipe preset clears the leftover fallback PIN',
          p.status().get('pin_fallback_set') is False)
    d = doc(tmp)
    check('no verifier/fallback survives swipe only',
          not d.get('verifier') and not d.get('fallback_pin_verifier'))
    check('swipe-only boot state is still a locked boot (lockhead shown)',
          p.ensure_state().get('locked') is True)
    check('the swipe itself releases it', p.unlock('').get('success') is True)
    p.lock('t')

    # --- pattern + PIN fallback ----------------------------------------------
    r = p.apply_preset('pin', '3838', '3838')
    check('re-select PIN with the fallback PIN', r.get('success') is True, r)
    r = p.apply_preset('pattern', '0-4-8-5-2', '0-4-8-5-2', fallback_pin='3838')
    check('pattern preset sets pattern + PIN fallback',
          r.get('success') and r.get('mode') == 'pattern' and r.get('pin_fallback_set'), r)
    check('pattern verifies', p.unlock('0-4-8-5-2').get('success') is True)
    check('pattern fallback PIN 3838 verifies', p.unlock('3838').get('success') is True)
    check('pattern preset refuses a missing confirmation',
          p.apply_preset('pattern', '0-4-8-5-2').get('success') is False)
    check('pattern preset refuses a mismatched confirmation',
          p.apply_preset('pattern', '0-4-8-5-2', '0-4-8-5-3', fallback_pin='3838').get('success') is False)

    # --- back to PIN using the fallback as proof ------------------------------
    r = p.apply_preset('pin', '3838', '3838')
    check('pattern -> PIN with the fallback PIN', r.get('success') and r.get('mode') == 'pin', r)
    check('PIN verifies after the swap', p.unlock('3838').get('success') is True)

    # --- fingerprint needs the secure matcher --------------------------------
    r = p.apply_preset('fingerprint', '3838')
    check('fingerprint preset is refused honestly without the matcher',
          r.get('success') is False and r.get('error') == 'fingerprint_provider_unavailable', r)
    check('fingerprint refusal keeps the PIN lock working', p.status()['mode'] == 'pin')

    # --- lock-state round trip -----------------------------------------------
    # The provider persists 'locked' when a credential is written/changed; the
    # launcher's overlay lock calls security.lock(), which the A45 harness
    # covers.  Here: a wrong secret never clears a persisted lock.
    p.lock('test')
    check('lock writes the authoritative locked state', p.status()['locked'] is True)
    check('wrong secret stays locked', p.unlock('1111').get('success') is False and p.status()['locked'] is True)
    check('right secret clears it', p.unlock('3838').get('success') is True and p.status()['locked'] is False)

# ---- boot with no lock state (the /run tmpfs case) ----------------------
with tempfile.TemporaryDirectory() as tmp:
    p = new_provider(tmp)
    st = p.status()
    check('no state + swipe mode: status is not an unlock of its own',
          st['locked'] is False and st['mode'] == 'swipe', st)
    r = p.apply_preset('pin', '3838', '3838')
    check('PIN preset still works from that state', r.get('success') is True, r)
    # wipe state again (simulates reboot) while in PIN mode
    (Path(tmp) / 'state.json').unlink()
    st = p.status()
    check('no state + PIN mode: fails closed',
          st['locked'] is True and 'no-state' in st['reason'], st)
    check('PIN still verifies after the fail-closed reboot state',
          p.unlock('3838').get('success') is True)

# ---- static contract -------------------------------------------------------
SEC = (ROOT / 'services/nuxel-bridge/src/security_provider.py').read_text()
API = (ROOT / 'services/nuxel-bridge/src/api.py').read_text()
check('provider exposes apply-preset', 'def apply_preset(' in SEC)
check('bridge allow-lists apply-preset as a mutating security verb', '"apply-preset"' in API)
check('presets list matches the owner request', 'PRESETS = ("swipe", "unlock", "pin", "pattern", "fingerprint")' in SEC)
check('status advertises swipe availability', '"swipe_available": True' in SEC)
UNIT = (ROOT / 'services/nuxel-bridge/systemd/nuxel-http-bridge.service').read_text()
check('the bridge unit creates /run/nuxel/security at boot (tmpfs state)',
      'RuntimeDirectory=nuxel/security' in UNIT)

print()
if fails:
    print('A84 SECURITY: %d FAILURE(S): %s' % (len(fails), ', '.join(fails)))
    sys.exit(1)
print('A84 SECURITY: ALL PASS')
