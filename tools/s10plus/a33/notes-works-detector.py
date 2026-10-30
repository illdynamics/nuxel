#!/usr/bin/env python3
"""Watch the focused Nuxel Notes Title for a fresh literal `works` entry.

PASS requires ALL of the following, observed from the live application:

  * a live AT-SPI Title entry named "Title" that is FOCUSED + SHOWING + EDITABLE;
  * its Text value contains the whole word `works`;
  * the value is fresh: either it differs from the baseline captured before
    playback, or the Title visibly changed away from the baseline and back
    (this covers a post-reboot run where the old text was already `works`);
  * when the bridge storage interface is reachable, a note with the same Title
    has been persisted after the baseline (the app's own autosave), so stale
    saved text can never satisfy the check.

The detector never treats a player exit code as confirmation.  Exit 0 = fresh
PASS, 1 = timeout, 2 = AT-SPI or Notes app unavailable.

AT-SPI is a session bus on this image: /run/nuxel-wayland/at-spi/bus.  The
previous version imported Atspi without setting AT_SPI_BUS_ADDRESS, so it died
with "Couldn't connect to accessibility bus" even though the live Notes entry
was visible.  The bus is discovered here before gi is imported.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

WORD = re.compile(r'(?<!\w)works(?!\w)', re.IGNORECASE)
API = os.environ.get('NUXEL_API_URL', 'http://127.0.0.1:8080/api/v1/rpc')


def _discover_atspi_bus():
    """Point Atspi at the live Nuxel session bus before importing gi.

    Order matters: libatspi reads AT_SPI_BUS_ADDRESS when it initialises, so a
    value set after ``import gi`` / ``Atspi.init()`` is too late.
    """
    runtime = os.environ.get('XDG_RUNTIME_DIR', '/run/nuxel-wayland')
    candidates = [
        os.environ.get('AT_SPI_BUS_ADDRESS'),
        'unix:path=%s/at-spi/bus' % runtime,
        'unix:path=/run/nuxel-wayland/at-spi/bus',
    ]
    for addr in candidates:
        if not addr:
            continue
        if addr.startswith('unix:path='):
            path = addr.split('=', 1)[1]
            if os.path.exists(path):
                os.environ['AT_SPI_BUS_ADDRESS'] = addr
                break
        else:
            os.environ['AT_SPI_BUS_ADDRESS'] = addr
            break
    if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        for path in ('/run/nuxel-wayland/bus', '/run/user/%d/bus' % os.getuid()):
            if os.path.exists(path):
                os.environ['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=%s' % path
                break


_discover_atspi_bus()

try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
except Exception as exc:  # pragma: no cover - live host only
    print(json.dumps({'result': 'ATSPI_UNAVAILABLE', 'error': str(exc)}))
    sys.exit(2)


def _rpc(app_id, namespace, verb, params):
    body = json.dumps({'app_id': app_id, 'namespace': namespace,
                       'verb': verb, 'params': params}).encode()
    req = urllib.request.Request(API, data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=4) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))


def store_notes():
    """Read the app's bridge-backed store read-only.

    Returns (notes, available, detail).  ``available`` is True when the bridge
    answered the storage RPC successfully, even if the key is still missing.
    The Notes app writes this key about one second after an input event.
    """
    try:
        doc = _rpc('nuxel-notes', 'storage', 'read', {'key': 'nuxel-notes'})
    except Exception as exc:
        return None, False, 'store RPC unavailable: %s' % exc
    result = doc.get('result') if isinstance(doc, dict) else None
    if not isinstance(result, dict) or result.get('success') is False:
        return None, False, 'store read failed: %s' % (result or doc)
    data = result.get('data')
    if data is None:
        return [], True, 'store key missing'
    if not isinstance(data, list):
        return [], True, 'store data is not a note list'
    return data, True, 'store readable'


def parse_iso(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def store_match(title, baseline_epoch):
    """Return (matched, detail, available, updated_at)."""
    notes, available, detail = store_notes()
    if not available:
        return None, detail, False, None
    for note in notes or []:
        if not isinstance(note, dict):
            continue
        if (note.get('title') or '').strip() != (title or '').strip():
            continue
        updated = parse_iso(note.get('updatedAt'))
        if updated is not None and updated + 2.0 < baseline_epoch:
            continue
        return True, 'persisted title matches', True, note.get('updatedAt')
    return False, detail, True, None


def iter_accessible(node, depth=0):
    if depth > 40:
        return
    yield node
    try:
        for i in range(node.get_child_count()):
            child = node.get_child_at_index(i)
            if child is not None:
                yield from iter_accessible(child, depth + 1)
    except Exception:
        return


def snapshot():
    entries = []
    apps = []
    try:
        desktop = Atspi.get_desktop(0)
    except Exception as exc:
        return [], [], 'AT-SPI desktop unavailable: %s' % exc
    for node in iter_accessible(desktop):
        try:
            role = node.get_role_name()
            name = node.get_name() or ''
            if role == 'application':
                apps.append(name)
            if role != 'entry':
                continue
            states = node.get_state_set()
            count = Atspi.Text.get_character_count(node)
            text = Atspi.Text.get_text(node, 0, count) if count >= 0 else ''
            entries.append({
                'name': name,
                'focused': bool(states.contains(Atspi.StateType.FOCUSED)),
                'showing': bool(states.contains(Atspi.StateType.SHOWING)),
                'editable': bool(states.contains(Atspi.StateType.EDITABLE)),
                'text': text,
                'is_title': name.strip().lower() == 'title',
            })
        except Exception:
            continue
    return entries, apps, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--timeout', type=float, default=240.0)
    ap.add_argument('--out', default='/root/pwnage-40000/evidence')
    ap.add_argument('--poll', type=float, default=0.2)
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / 'notes-works-poll.jsonl'
    baseline_path = out_dir / 'notes-works-baseline.json'
    result_path = out_dir / 'notes-works-result.json'

    try:
        Atspi.init()
    except Exception:
        pass

    entries, apps, err = snapshot()
    if err:
        result = {'result': 'ATSPI_UNAVAILABLE', 'error': err, 'at': time.time()}
        result_path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        return 2
    title = next((e for e in entries if e['is_title']), None)
    baseline = title['text'] if title else None
    baseline_epoch = time.time()
    baseline_doc = {
        'at': baseline_epoch, 'title': baseline, 'entries': entries,
        'applications': apps,
        'at_spi_bus': os.environ.get('AT_SPI_BUS_ADDRESS'),
        'note': 'baseline captured before the confirmation playback',
    }
    baseline_path.write_text(json.dumps(baseline_doc, indent=2) + '\n')
    if title is None:
        result = {'result': 'NO_TITLE_ENTRY', 'at': time.time(), 'entries': entries,
                  'applications': apps}
        result_path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        return 2

    deadline = time.monotonic() + max(1.0, args.timeout)
    last = None
    changed_away = False
    last_event_at = 0.0
    with log_path.open('a') as log:
        while time.monotonic() < deadline:
            entries, apps, err = snapshot()
            title = next((e for e in entries if e['is_title']), None)
            state = title['text'] if title else None
            if state != last:
                rec = {'at': time.time(), 'title': state,
                       'focused': bool(title and title['focused']),
                       'showing': bool(title and title['showing']),
                       'editable': bool(title and title['editable']),
                       'baseline': baseline}
                log.write(json.dumps(rec, sort_keys=True) + '\n')
                log.flush()
                last = state
                last_event_at = time.time()
            if state is not None and state != baseline:
                changed_away = True
            fresh = (state is not None and state != baseline) or (changed_away and state == baseline)
            if title and title['focused'] and title['showing'] and title['editable'] \
                    and fresh and WORD.search(state or ''):
                # The app autosaves about one second after input.  Wait briefly
                # for the bridge store to corroborate the same fresh Title.
                matched = None
                detail = 'store not checked'
                available = False
                updated = None
                store_deadline = time.monotonic() + 3.0
                while True:
                    matched, detail, available, updated = store_match(state, baseline_epoch)
                    if not available or matched:
                        break
                    if time.monotonic() >= store_deadline:
                        break
                    time.sleep(0.25)
                if available and not matched:
                    # The UI text is fresh, but the app has not persisted it.
                    # Do not call that a PASS yet; keep watching.
                    time.sleep(args.poll)
                    continue
                result = {
                    'result': 'PASS', 'at': time.time(), 'title': state,
                    'baseline': baseline, 'changed_away': changed_away,
                    'focused': True, 'showing': True, 'editable': True,
                    'on_change': last_event_at > 0,
                    'store_available': available,
                    'store_matches': matched,
                    'store_updated_at': updated,
                    'store_detail': detail,
                    'at_spi_bus': os.environ.get('AT_SPI_BUS_ADDRESS'),
                    'applications': apps,
                    'evidence': 'live focused Title contains the whole word works '
                                'and is fresh relative to the baseline',
                }
                result_path.write_text(json.dumps(result, indent=2) + '\n')
                print(json.dumps(result))
                return 0
            time.sleep(args.poll)
    result = {'result': 'TIMEOUT', 'at': time.time(), 'baseline': baseline,
              'last_title': last, 'changed_away': changed_away,
              'at_spi_bus': os.environ.get('AT_SPI_BUS_ADDRESS')}
    result_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 1


if __name__ == '__main__':
    sys.exit(main())
