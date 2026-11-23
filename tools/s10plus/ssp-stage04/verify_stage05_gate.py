#!/usr/bin/env python3
"""Fail-closed JSON gate for SSP Stage 05; checks reported facts, NOT hardware.

Stage 05 requires a NEW independently evidenced preflight receipt containing
all named PASS gates below. This utility deliberately rejects the original
Stage-04 NO_FLASH receipt, PARTIAL, PASS_WITH_CAVEAT, and missing fields.
It cannot establish TWRP access, authenticate a log, validate a live partition
or authorize flash; device-side verification remains a separate requirement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

MANDATORY = (
    'G_TEST_NATIVE_C_HARNESS',
    'G_TEST_ORIENTATION_PYTEST',
    'G_TEST_RECOVERY_UNITTEST',
    'G_TEST_SSP_BOOT_PACKER',
    'G_TEST_KERNEL_SOURCE_AUDIT',
    'G_KERNEL_CLEAN_INPUTS',
    'G_KERNEL_BUILD_EXACT_PINNED',
    'G_SSP_PATCH_RECEIPTS',
    'G_EMBEDDED_FIRMWARE_IDENTITY',
    'G_BOOT_DONOR_REVALIDATION',
    'G_BOOT_PACK_VERIFY',
    'G_BOOT_BYTEEXACT_TAIL',
    'G_BOOT_DTB_DTBO_PARTITION_HASHES',
    'G_BOOT_ROLLBACK_STAGING',
    'G_TWRP_PARTITION_MAPPING',
    'G_SOFTWARE_ONLY_ALTERNATIVE_REVIEW',
    'G_EXPLICIT_BOUND_TRIAL_AUTHORIZATION',
)


def validate(d: dict) -> dict:
    gates = d.get('gates', {})
    results = {k: (gates.get(k, {}).get('status', 'MISSING') if
                   isinstance(gates.get(k, {}), dict) else 'MALFORMED')
               for k in MANDATORY}
    wrong = {k: v for k, v in results.items() if v != 'PASS'}
    verdict = d.get('overall_verdict', 'MISSING')
    issues = []
    if verdict != 'PASS':
        issues.append('overall_verdict must equal PASS')
    if wrong:
        issues.append('missing/non-PASS gates: ' + ', '.join(f'{k}={v}' for k, v in wrong.items()))
    return {'verdict': 'PASS_REPORTED_GATES_ONLY' if not issues else 'NO_FLASH',
            'warnings': ['Reported PASS gates still require independent physical/current-session verification before BOOT write'],
            'issues': issues, 'gate_statuses': results}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preflight', type=Path, required=True)
    p.add_argument('--json-out', type=Path)
    a=p.parse_args(argv)
    try:
        result=validate(json.loads(a.preflight.read_text()))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        result={'verdict':'NO_FLASH', 'issues':[f'cannot read preflight: {e}']}
    if a.json_out:
        a.json_out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['verdict']=='PASS_REPORTED_GATES_ONLY' else 1


if __name__=='__main__':
    sys.exit(main())
