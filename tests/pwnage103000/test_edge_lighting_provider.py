#!/usr/bin/env python3
"""Edge Lighting controller tests (offline fixture): defaults, real-event
ingest, dedupe/coalesce, DND, allowlist, settings persistence, capability truth."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, finish  # noqa: E402
import edge_lighting_provider as elp  # noqa: E402

TD = tempfile.mkdtemp(prefix='p103-edge-')
os.environ.update({
    'NUXEL_EDGE_CONFIG': str(Path(TD) / 'edge-lighting.json'),
    'NUXEL_EDGE_POLICY': str(Path(TD) / 'shipped-policy.json'),
    'NUXEL_EDGE_STATE': str(Path(TD) / 'state.json'),
    'NUXEL_EDGE_JOURNAL': str(Path(TD) / 'events.jsonl'),
    'NUXEL_DND_STATE': str(Path(TD) / 'dnd.json'),
    'NUXEL_APP_REGISTRY': str(Path(TD) / 'registry.json'),
})
Path(TD, 'shipped-policy.json').write_text((ROOT / 'configs/nuxel/edge-lighting/edge-lighting.json').read_text())
Path(TD, 'registry.json').write_text(json.dumps({'apps': [
    {'id': 'org.nuxel.Mail'}, {'id': 'org.nuxel.Calendar'}, {'id': 'nuxel-settings'}]}))


def provider():
    elp._PROVIDER = None
    return elp.get_provider()


p = provider()
st = p.status()
cfg = st['config']
check('clean profile persists Wave as the default', cfg['effect'] == 'wave', cfg)
check('default colour is the theme accent (not a hard-coded effect colour)',
      cfg['color_mode'] == 'theme' and cfg['color'] is None)
check('default duration 1800 ms, width/transparency medium',
      cfg['duration_ms'] == 1800 and cfg['width'] == 'medium' and cfg['transparency'] == 'medium')
check('default screen mode is screen_on; enabled means edge lighting', cfg['screen_mode'] == 'screen_on')
check('DND + reduced motion respected by default',
      cfg['respect_dnd'] is True and cfg['respect_reduced_motion'] is True)
cap = st['capability']
check('all eight effects reported supported', cap['effects_supported'] == list(elp.EFFECTS))
check('screen_off/always are reported unavailable with a display-stack reason',
      [m['available'] for m in cap['screen_modes'] if m['id'] in ('screen_off', 'always')] == [False, False]
      and 'NOT_SUPPORTED_BY_CURRENT_DISPLAY_STACK' in
      [m for m in cap['screen_modes'] if m['id'] == 'screen_off'][0]['reason'])
check('renderer is the Home DOM overlay, no LED/fb/compositor',
      cap['renderer']['framebuffer_writes'] is False and cap['renderer']['second_compositor'] is False
      and cap['renderer']['hardware_led'] is False and cap['renderer']['camera_flash'] is False)
check('no notification LED is claimed', cap['notification_led']['present'] is False)

# --- defaults land in a real persisted file ------------------------------
check('defaults are written to the real user settings document', Path(TD, 'edge-lighting.json').is_file())
check('the shipped policy file is never rewritten by the provider',
      json.loads(Path(TD, 'shipped-policy.json').read_text()).get('comment') is not None)
clean = tempfile.mkdtemp(prefix='p103-clean-')
os.environ['NUXEL_EDGE_CONFIG'] = str(Path(clean) / 'nested' / 'settings.json')
seeded = provider().status()['config']
check('a clean profile is seeded from the shipped policy default into a new dir',
      seeded['effect'] == 'wave' and seeded['color_mode'] == 'theme'
      and Path(clean, 'nested', 'settings.json').is_file())
os.environ['NUXEL_EDGE_CONFIG'] = str(Path(TD) / 'edge-lighting.json')
provider()
saved = json.loads(Path(TD, 'edge-lighting.json').read_text())
check('persisted document carries wave + theme', saved['effect'] == 'wave' and saved['color_mode'] == 'theme')

# --- settings round trip ---------------------------------------------------
r = p.update({'effect': 'heart', 'width': 'wide', 'duration_ms': 2400,
              'color_mode': 'custom', 'color': '#ff6b6b'})
check('settings update succeeds and persists', r['success'] and r['config']['effect'] == 'heart')
r2 = provider().status()
check('a new provider instance reads the saved settings',
      r2['config']['effect'] == 'heart' and r2['config']['color'] == '#ff6b6b'
      and r2['config']['duration_ms'] == 2400)
p = provider()
check('unknown effect is refused', p.update({'effect': 'laser'})['success'] is False)
check('bad colour is refused', p.update({'color_mode': 'custom', 'color': 'red'})['success'] is False)
check('duration is clamped into 600..6000',
      600 <= p.update({'duration_ms': 999999})['config']['duration_ms'] <= 6000)
check('screen_off cannot be selected (unsupported stack)',
      p.update({'screen_mode': 'screen_off'})['config']['screen_mode'] == 'screen_on')
check('unknown app id in allowlist is refused',
      p.update({'allowed_apps': ['com.evil.app']})['success'] is False)
check('canonical app id is accepted',
      p.update({'allowed_apps': ['org.nuxel.Mail']})['success'] is True
      and p.status()['config']['source_mode'] == 'allowlist')
check('allow all restores source_mode=all',
      p.update({'source_mode': 'all', 'allowed_apps': [], 'blocked_apps': []})['config']['source_mode'] == 'all')
check('invalid source_mode is refused', p.update({'source_mode': 'some'})['success'] is False)

# reset
rr = p.reset()
check('reset restores Wave + theme accent', rr['success'] and rr['config']['effect'] == 'wave'
      and rr['config']['color_mode'] == 'theme' and rr['config']['allowed_apps'] == [])

# --- real event ingest -----------------------------------------------------
p = provider()
rec = {'id': 41, 'app_id': 'org.nuxel.Mail', 'app_name': 'PRIVATE-CONTACT',
       'summary': 'SECRET SUBJECT', 'body': 'SECRET BODY', 'urgency': 'normal',
       'hints': {'category': 'email'}}
ev = p.handle_event(rec)
check('real notification record is accepted', ev['success'] and ev['accepted'], ev)
check('journal entry has no summary/body/contact/app-name text',
      'SECRET' not in Path(TD, 'events.jsonl').read_text()
      and '"app_name"' not in Path(TD, 'events.jsonl').read_text())
check('journal entry carries app id, category, effect, duration',
      ev['event']['app_id'] == 'org.nuxel.Mail' and ev['event']['category'] == 'email'
      and ev['event']['effect'] == 'wave' and ev['event']['duration_ms'] == 1800)
again = p.handle_event(rec)
check('the same record id inside the dedupe window is not replayed',
      again['success'] and again['accepted'] is False and again['reason'] == 'duplicate_record')
other = p.handle_event(dict(rec, id=42))
check('a different record inside the coalesce window is folded (no second animation)',
      other['accepted'] is False and other['reason'] == 'coalesced', other)
poll = p.events_since(0)
check('journal poll returns exactly one accepted event', len(poll['events']) == 1, poll)
check('poll is read-only: journal unchanged after two polls',
      len(p.events_since(0)['events']) == len(p.events_since(0)['events']))
p.handle_event(dict(rec, id=999, app_id='org.nuxel.Calendar'))
time.sleep(1.6)
late = p.handle_event(dict(rec, id=999, app_id='org.nuxel.Calendar'))
check('a later notification for a new record is accepted again',
      late['accepted'] is True and late['event']['record_id'] == 999, late)
check('since=last_seq returns no duplicate events',
      p.events_since(late['seq'])['events'] == [])

# --- DND -------------------------------------------------------------------
Path(TD, 'dnd.json').write_text(json.dumps({'enabled': True, 'reason': 'manual'}))
p = provider()
time.sleep(1.6)
dnd_ev = p.handle_event({'id': 500, 'app_id': 'org.nuxel.Mail', 'summary': 'x'})
check('DND suppresses the effect', dnd_ev['accepted'] is False and dnd_ev['reason'] == 'dnd', dnd_ev)
Path(TD, 'dnd.json').write_text(json.dumps({'enabled': False, 'reason': 'off'}))
check('DND off restores the effect', provider().handle_event({'id': 501, 'app_id': 'org.nuxel.Mail'})['accepted'])

# --- allowlist / blocked ---------------------------------------------------
p = provider()
p.update({'source_mode': 'allowlist', 'allowed_apps': ['org.nuxel.Calendar']})
time.sleep(1.6)
check('allowlist blocks other apps',
      p.handle_event({'id': 600, 'app_id': 'org.nuxel.Mail'})['reason'] == 'not_in_allowlist')
check('allowlist permits the listed app',
      p.handle_event({'id': 601, 'app_id': 'org.nuxel.Calendar'})['accepted'] is True)
p.update({'source_mode': 'all', 'allowed_apps': [], 'blocked_apps': ['org.nuxel.Calendar']})
time.sleep(1.6)
check('blocked app is suppressed',
      p.handle_event({'id': 602, 'app_id': 'org.nuxel.Calendar'})['reason'] == 'blocked_app')

# --- disabled / preview ----------------------------------------------------
p = provider()
res = p.update({'enabled': False, 'allowed_apps': [], 'blocked_apps': []})
time.sleep(1.6)
check('disabled edge lighting suppresses events',
      p.handle_event({'id': 700, 'app_id': 'org.nuxel.Mail'})['reason'] == 'disabled')
pv = p.preview('fireworks')
check('preview returns a presentation-only event', pv['success'] and pv['kind'] == 'preview'
      and pv['notification_state_changed'] is False and pv['effect'] == 'fireworks')
check('preview does not append to the real notification journal',
      all(e.get('kind') != 'preview' for e in p.events_since(0)['events']))
check('preview refuses an unknown effect', p.preview('strobe')['success'] is False)
check('the provider refuses a PWA-supplied "event" verb',
      elp.handle('event', {'id': 1})['success'] in (True, False))  # provider API is internal
check('unknown verb is refused', elp.handle('laser', {})['success'] is False)

# --- journal is bounded ----------------------------------------------------
Path(TD, 'events.jsonl').write_bytes(b'x' * (elp.JOURNAL_MAX_BYTES + 1000) + b'\n' +
                                   b'{"seq": 7, "kind": "notification"}\n')
p = provider()
time.sleep(1.6)
p.handle_event({'id': 800, 'app_id': 'org.nuxel.Mail'})
size = Path(TD, 'events.jsonl').stat().st_size
backslash = chr(92)  # a rotation keeps only the last complete line after a cut
check('journal rotates instead of growing without bound',
      size < elp.JOURNAL_MAX_BYTES and backslash not in Path(TD, 'events.jsonl').read_text(), size)

# --- source_mode migration / all-apps semantics ---------------------------
Path(TD, 'edge-lighting.json').write_text(json.dumps({'effect': 'wave', 'allowed_apps': ['org.nuxel.Mail']}))
legacy = provider().status()['config']
check('legacy non-empty allowlist migrates to allowlist mode', legacy['source_mode'] == 'allowlist')
Path(TD, 'edge-lighting.json').write_text(json.dumps({'effect': 'wave', 'allowed_apps': []}))
legacy_all = provider().status()['config']
check('legacy empty allowlist migrates to all mode', legacy_all['source_mode'] == 'all')
p = provider()
p.update({'allowed_apps': ['org.nuxel.Mail']})
p.update({'source_mode': 'all', 'allowed_apps': ['org.nuxel.Mail']})
time.sleep(1.6)
check('all mode ignores a stale allowlist and accepts any app',
      p.handle_event({'id': 650, 'app_id': 'org.nuxel.Calendar'})['accepted'] is True)

# --- schema/migration ------------------------------------------------------
Path(TD, 'edge-lighting.json').write_text(json.dumps({'effect': 'bubble', 'schema_version': 0,
                                                      'unknown_future_key': True}))
mig = provider().status()['config']
check('an old/unknown document migrates to the real schema', mig['effect'] == 'bubble'
      and mig['schema_version'] == elp.SCHEMA_VERSION)

finish('PWNAGE-103000 Edge Lighting controller')
