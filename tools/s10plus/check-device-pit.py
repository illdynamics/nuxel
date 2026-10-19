#!/usr/bin/env python3
"""Safe, read-only preflight for an S10+ Heimdall flash.

Three *separate* questions are answered, because they have different evidence
and different failure modes:

  [1] PIT structural check   - is this the expected Exynos 9820 (LSI9820) PIT?
  [2] CAPACITY check         - does BOOT / USERDATA actually fit in bytes?
  [3] BOARD REVISION check   - does the image's board overlay match the phone?

A PIT text dump cannot answer [2] byte-exactly (it has no trustworthy block
unit) and cannot answer [3] at all. Those require facts the operator supplies
from an independent, trusted source. This script therefore never upgrades an
"unknown" to a "pass": it reports each verdict separately and exits non-zero
unless every required verdict is positively verified.

Exit codes:
  0  all checks verified
  1  PIT structural failure (hard stop)
  2  capacity not verified, or image exceeds verified capacity
  3  board revision not verified or mismatch
  4  capacity and board revision both unverified
"""
import argparse
import json
import pathlib
import re
import sys

FIELDS = ('Partition Name', 'Partition Block Count',
          'Partition Block Size/Offset', 'Device Type', 'Identifier')

REQUIRED = ('DTB', 'DTBO', 'BOOT', 'USERDATA', 'SYSTEM')
PROTECTED = ('BOOTLOADER', 'BOOTLOADER2', 'PIT', 'MD5HDR', 'EFS', 'SEC_EFS',
             'PARAM', 'UP_PARAM', 'KEYSTORAGE', 'RECOVERY', 'KEYREFUGE',
             'KEYDATA', 'VBMETA', 'CPEFS', 'CP_DEBUG')


def entries_from_text(data):
    header = re.search(r'CPU/bootloader tag:\s*(\S+)', data)
    if not header:
        raise ValueError('missing CPU/bootloader tag')
    rows = []
    for raw in re.split(r'^--- Entry #\d+ ---\s*$', data, flags=re.M)[1:]:
        row = {}
        for field in FIELDS:
            m = re.search(r'^' + re.escape(field) + r':\s*(\S+)', raw, re.M)
            if m:
                row[field] = m.group(1)
        if 'Partition Name' in row:
            rows.append(row)
    return header.group(1), rows


def check_structure(cpu, rows, expected_count):
    if cpu != 'LSI9820':
        raise ValueError('expected Exynos LSI9820, found ' + cpu)
    names = {r.get('Partition Name'): r for r in rows}
    for part in REQUIRED:
        if part not in names:
            raise ValueError('required entry missing: ' + part)
    if expected_count and len(rows) != expected_count:
        raise ValueError('expected %d PIT entries; found %d' % (expected_count, len(rows)))
    for key in ('BOOT', 'USERDATA'):
        if names[key].get('Device Type') != '8':
            raise ValueError('unexpected non-UFS partition ' + key)
    return names


def check_capacity(names, images, verified_block_bytes):
    """Return (verdict, details). verdict in VERIFIED|UNVERIFIED|FAIL."""
    details = []
    verdict = 'UNVERIFIED'
    any_checked = False
    for key, path in images:
        row = names[key]
        count = int(row['Partition Block Count'])
        details.append({'partition': key,
                        'pit_block_count': count,
                        'pit_unit': row.get('Partition Block Size/Offset'),
                        'image_bytes': path.stat().st_size if path else None})
        if path is None:
            # No image supplied for this partition: nothing to verify here.
            continue
        any_checked = True
        size = path.stat().st_size
        if count == 0:
            # Extends to disk end; the PIT gives no byte capacity.
            verdict = 'UNVERIFIED'
        elif verified_block_bytes:
            capacity = count * verified_block_bytes
            details[-1]['verified_capacity_bytes'] = capacity
            if size > capacity:
                return 'FAIL', details
            verdict = 'VERIFIED'
        else:
            # Non-zero block count, but no independently-verified byte unit.
            verdict = 'UNVERIFIED'
    if not any_checked:
        verdict = 'UNVERIFIED'
    return verdict, details


def check_board_revision(image_overlay, device_rev):
    """Return (verdict, note). verdict in MATCH|MISMATCH|UNKNOWN."""
    if not device_rev or not image_overlay:
        return 'UNKNOWN', 'operator did not supply both the phone board revision and the image overlay string'
    rev_match = re.search(r'(\d+)\s*$', image_overlay)
    if not rev_match:
        return 'UNKNOWN', 'could not parse a revision number from the image overlay string'
    if rev_match.group(1) == str(device_rev).strip():
        return 'MATCH', 'image overlay revision %s matches the supplied phone board revision' % rev_match.group(1)
    return 'MISMATCH', 'image overlay revision %s does NOT match phone board revision %s' % (
        rev_match.group(1), device_rev)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('pit', type=pathlib.Path, help='text from heimdall print-pit')
    p.add_argument('--boot', type=pathlib.Path, help='boot image to check')
    p.add_argument('--rootfs', type=pathlib.Path, help='USERDATA/rootfs image to check')
    p.add_argument('--verified-block-bytes', type=int, choices=[512, 4096, 8192],
                   help='ONLY if independently verified for this device; never infer from PIT')
    p.add_argument('--board-rev', help='independently verified phone hardware revision (e.g. 26)')
    p.add_argument('--image-overlay', help='board overlay string embedded in the image (e.g. "BEYOND2LTE EUR OPEN 26")')
    p.add_argument('--expected-entries', type=int, default=41,
                   help='expected PIT entry count (default 41 for the supplied reference)')
    p.add_argument('--json', action='store_true', help='emit a machine-readable summary')
    args = p.parse_args()

    result = {'structure': 'FAIL', 'capacity': 'UNVERIFIED',
              'board_revision': 'UNKNOWN', 'notes': []}

    try:
        cpu, rows = entries_from_text(args.pit.read_text(errors='replace'))
        names = check_structure(cpu, rows, args.expected_entries)
        result['structure'] = 'PASS'
    except (OSError, ValueError) as e:
        print('PIT CHECK FAILED (structural): ' + str(e), file=sys.stderr)
        result['notes'].append(str(e))
        if args.json:
            print(json.dumps(result))
        return 1

    if not args.json:
        print('[1/3] PIT structural check  : PASS '
              '(LSI9820, %d entries, DTB/DTBO/BOOT/SYSTEM/USERDATA present)' % len(rows))
        print('      protected partitions present and never targeted: '
              + ', '.join(sorted(set(PROTECTED) & set(names))))

    capacity_verdict, capacity_details = check_capacity(
        names, (('BOOT', args.boot), ('USERDATA', args.rootfs)), args.verified_block_bytes)
    result['capacity'] = capacity_verdict
    result['capacity_details'] = capacity_details

    if not args.json:
        print('[2/3] CAPACITY check        : %s' % capacity_verdict)
        for d in capacity_details:
            unit = d['pit_unit']
            print('      %-8s PIT blocks=%s unit(slot)=%s image_bytes=%s%s'
                  % (d['partition'], d['pit_block_count'], unit, d['image_bytes'],
                     '  verified_capacity_bytes=%s' % d['verified_capacity_bytes']
                     if 'verified_capacity_bytes' in d else ''))
        if capacity_verdict == 'UNVERIFIED':
            print('      -> USERDATA count=0 extends to disk end and/or no --verified-block-bytes.')
            print('      -> An PIT text dump has no trustworthy byte unit. Verify separately.')

    rev_verdict, rev_note = check_board_revision(args.image_overlay, args.board_rev)
    result['board_revision'] = rev_verdict
    result['board_revision_note'] = rev_note

    if not args.json:
        print('[3/3] BOARD REVISION check  : %s' % rev_verdict)
        print('      %s' % rev_note)
        print('      -> A PIT cannot reveal the board revision. This must come from the')
        print('         phone itself (bootloader/recovery) or model+rev-matched stock firmware.')

    if capacity_verdict == 'FAIL' or rev_verdict == 'MISMATCH':
        code = 2 if capacity_verdict == 'FAIL' else 3
    elif capacity_verdict == 'UNVERIFIED' and rev_verdict == 'UNKNOWN':
        code = 4
    elif capacity_verdict == 'UNVERIFIED':
        code = 2
    elif rev_verdict != 'MATCH':
        code = 3
    else:
        code = 0

    result['exit_code'] = code
    result['verdict'] = 'VERIFIED' if code == 0 else 'NOT_VERIFIED'

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print('VERDICT: %s (exit %d)' % (result['verdict'], code))
        if code != 0:
            print('Do NOT treat this as approval to flash an unverified board/image.')

    return code


if __name__ == '__main__':
    sys.exit(main())
